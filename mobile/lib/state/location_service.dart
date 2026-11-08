import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

import '../api/api_client.dart';

/// Shares the truck's position with operations while a trip is under way.
///
/// - Fixes come from the OS location stream (every ~50 m of movement), plus a
///   heartbeat fix every few minutes when parked (border queues, weighbridges),
///   so operations can tell "stopped" from "phone off".
/// - Fixes are buffered and sent in batches; if there's no signal they are kept
///   (up to [_maxBuffer]) and sent when the connection returns.
/// - On Android a foreground service with a visible notification keeps updates
///   running with the screen off; on iOS the "location" background mode does.
/// - Sharing stops when the trip ends: the server answers `tracking: false`.
///
/// Positions go to staff only. Cargo owners never see them.
class LocationService extends ChangeNotifier {
  LocationService(this.api);
  final ApiClient api;

  static const _flushEvery = Duration(seconds: 30);
  static const _heartbeatEvery = Duration(minutes: 3);
  static const _maxBuffer = 2000;

  String? tripCode;
  bool sharing = false;
  String? problem; // why sharing is not possible, for the UI
  DateTime? lastFixAt;
  DateTime? lastSentAt;
  Position? lastPosition;
  final List<Map<String, dynamic>> _buffer = [];
  StreamSubscription<Position>? _sub;
  Timer? _flushTimer, _heartbeat;
  bool _flushing = false;

  int get pending => _buffer.length;

  /// Start (or keep) sharing for [code]. Safe to call repeatedly.
  Future<void> start(String code) async {
    if (sharing && tripCode == code) return;
    await stop(flush: true);
    tripCode = code;
    problem = await _ensurePermission();
    if (problem != null) {
      notifyListeners();
      return;
    }
    _sub = Geolocator.getPositionStream(locationSettings: _settings()).listen(_onFix, onError: (Object e) {
      problem = 'Location stopped: $e';
      notifyListeners();
    });
    _flushTimer = Timer.periodic(_flushEvery, (_) => flush());
    _heartbeat = Timer.periodic(_heartbeatEvery, (_) => _beat());
    sharing = true;
    notifyListeners();
    _beat(); // first fix straight away
  }

  Future<void> stop({bool flush = true}) async {
    await _sub?.cancel();
    _sub = null;
    _flushTimer?.cancel();
    _heartbeat?.cancel();
    if (flush && _buffer.isNotEmpty) await this.flush();
    sharing = false;
    notifyListeners();
  }

  /// Ask again after the driver changed a setting.
  Future<void> retry() async {
    final code = tripCode;
    if (code == null) return;
    sharing = false;
    await start(code);
  }

  Future<void> openSettings() async {
    final perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.deniedForever) {
      await Geolocator.openAppSettings();
    } else {
      await Geolocator.openLocationSettings();
    }
  }

  Future<String?> _ensurePermission() async {
    if (!await Geolocator.isLocationServiceEnabled()) return 'Turn on location (GPS) so operations can see your truck.';
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
    if (perm == LocationPermission.denied) return 'Allow location access so operations can see your truck.';
    if (perm == LocationPermission.deniedForever) return 'Location is blocked for XpressDrive. Allow it in Settings.';
    return null;
  }

  LocationSettings _settings() {
    if (defaultTargetPlatform == TargetPlatform.android) {
      return AndroidSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 50,
        intervalDuration: const Duration(seconds: 20),
        foregroundNotificationConfig: const ForegroundNotificationConfig(
          notificationTitle: 'XpressDrive: trip in progress',
          notificationText: 'Sharing your truck location with operations until the trip ends.',
          enableWakeLock: true,
          setOngoing: true,
        ),
      );
    }
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      return AppleSettings(
        accuracy: LocationAccuracy.high,
        activityType: ActivityType.automotiveNavigation,
        distanceFilter: 50,
        pauseLocationUpdatesAutomatically: false,
        allowBackgroundLocationUpdates: true,
        showBackgroundLocationIndicator: true,
      );
    }
    return const LocationSettings(accuracy: LocationAccuracy.high, distanceFilter: 50);
  }

  void _onFix(Position p) {
    lastPosition = p;
    lastFixAt = DateTime.now();
    _buffer.add({
      'lat': p.latitude,
      'lng': p.longitude,
      if (p.speed >= 0) 'speed_kmh': (p.speed * 3.6).clamp(0, 300),
      if (p.heading >= 0 && p.heading <= 360) 'heading': p.heading,
      if (p.accuracy >= 0) 'accuracy_m': p.accuracy.clamp(0, 100000),
      'recorded_at': p.timestamp.toUtc().toIso8601String(),
    });
    if (_buffer.length > _maxBuffer) _buffer.removeRange(0, _buffer.length - _maxBuffer);
    notifyListeners();
  }

  Future<void> _beat() async {
    if (lastFixAt != null && DateTime.now().difference(lastFixAt!) < _heartbeatEvery) return;
    try {
      _onFix(await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 30))));
    } catch (_) {
      // No fix right now (tunnel, indoors); the stream will catch up.
    }
  }

  /// Send buffered fixes. Kept on failure so nothing is lost without signal.
  Future<void> flush() async {
    final code = tripCode;
    if (_flushing || code == null || _buffer.isEmpty) return;
    _flushing = true;
    final batch = _buffer.take(200).toList();
    try {
      final res = await api.post('/driver/trips/${Uri.encodeComponent(code)}/positions/', body: {'positions': batch});
      _buffer.removeRange(0, batch.length);
      lastSentAt = DateTime.now();
      problem = null;
      if (res is Map && res['tracking'] == false) {
        _buffer.clear();
        await stop(flush: false);
        tripCode = null;
      }
    } on ApiException catch (e) {
      if (e.status == 400) {
        _buffer.removeRange(0, batch.length); // e.g. a fix with a wrong clock: drop it rather than retry forever
      } else if (e.status == 403 || e.status == 404) {
        _buffer.clear();
        await stop(flush: false);
        tripCode = null;
      }
    } finally {
      _flushing = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    _flushTimer?.cancel();
    _heartbeat?.cancel();
    super.dispose();
  }
}
