import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../models/driver_models.dart';
import '../../state/location_service.dart';
import '../../widgets/parcel_ui.dart' show kInk;
import '../profile_screen.dart';
import 'driver_trips_screen.dart';
import 'empty_legs_screen.dart';

/// Home for drivers: allocations, return-space offers and account.
///
/// Polls /driver/summary/ every minute while the app is open so new allocations
/// from operations show up quickly, and keeps location sharing running for the
/// trip that is under way.
class DriverShell extends StatefulWidget {
  const DriverShell({super.key});
  @override
  State<DriverShell> createState() => _DriverShellState();
}

class _DriverShellState extends State<DriverShell> with WidgetsBindingObserver {
  int _index = 0;
  int _pending = 0;
  Set<String> _seenPending = {};
  Timer? _poll;
  final _tripsKey = GlobalKey<DriverTripsScreenState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _check(initial: true);
    _poll = Timer.periodic(const Duration(seconds: 60), (_) => _check());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _check();
  }

  Future<void> _check({bool initial = false}) async {
    final api = context.read<ApiClient>();
    final location = context.read<LocationService>();
    try {
      final s = await api.get('/driver/summary/') as Map<String, dynamic>;
      final pending = ((s['pending'] as List?) ?? []).map((e) => DriverTrip.fromJson(e as Map<String, dynamic>)).toList();
      final active = s['active_trip'] == null ? null : DriverTrip.fromJson(s['active_trip'] as Map<String, dynamic>);
      final codes = pending.map((t) => t.code).toSet();
      final fresh = codes.difference(_seenPending);
      if (!mounted) return;
      setState(() {
        _pending = pending.length;
        _seenPending = codes;
      });
      if (!initial && fresh.isNotEmpty) {
        final t = pending.firstWhere((x) => fresh.contains(x.code));
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('New trip allocated: ${t.route}'),
          action: SnackBarAction(label: 'View', onPressed: () => setState(() => _index = 0)),
          duration: const Duration(seconds: 8),
        ));
        _tripsKey.currentState?.reload();
      }
      if (active != null && active.isLive) {
        await location.start(active.code);
      } else if (location.sharing) {
        await location.stop();
      }
    } catch (_) {
      // Offline: try again on the next tick.
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      DriverTripsScreen(key: _tripsKey, onChanged: _check),
      const EmptyLegsScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      body: Column(children: [
        const _SharingBanner(),
        Expanded(child: IndexedStack(index: _index, children: pages)),
      ]),
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0xFFE0E6EE)))),
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: [
            NavigationDestination(
              icon: Badge(isLabelVisible: _pending > 0, label: Text('$_pending'), child: const Icon(Icons.local_shipping_outlined)),
              selectedIcon: const Icon(Icons.local_shipping),
              label: 'Trips',
            ),
            const NavigationDestination(icon: Icon(Icons.u_turn_left), selectedIcon: Icon(Icons.u_turn_left), label: 'Return space'),
            const NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Account'),
          ],
        ),
      ),
    );
  }
}

/// Always-visible strip while a trip is under way: is the location getting through?
class _SharingBanner extends StatelessWidget {
  const _SharingBanner();

  @override
  Widget build(BuildContext context) {
    final loc = context.watch<LocationService>();
    if (loc.tripCode == null) return const SizedBox.shrink();
    final ok = loc.sharing && loc.problem == null;
    return Material(
      color: ok ? const Color(0xFFE7F6ED) : const Color(0xFFFDECEA),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
          child: Row(children: [
            Icon(ok ? Icons.my_location : Icons.location_disabled, size: 18, color: ok ? const Color(0xFF1F9D55) : const Color(0xFFB42318)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                ok
                    ? 'Sharing location for ${loc.tripCode}${loc.pending > 0 ? ' · ${loc.pending} waiting for signal' : ''}'
                    : (loc.problem ?? 'Location sharing is off'),
                style: const TextStyle(fontSize: 13, color: kInk),
              ),
            ),
            if (!ok) TextButton(onPressed: () async {
              await loc.openSettings();
              await loc.retry();
            }, child: const Text('Fix')),
          ]),
        ),
      ),
    );
  }
}

