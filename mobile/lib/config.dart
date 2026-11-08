import 'package:flutter/foundation.dart';

/// API base URL. Override at build time:
///   flutter run --dart-define-from-file=.env   (see .env.example)
///   flutter run --dart-define=API_BASE_URL=https://api.widest.co.ug
/// Default targets the Android emulator's alias for the host machine.
const String apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:4444');

void assertSecureConfig() {
  // OWASP MASVS-NETWORK: never ship a release build that talks plain HTTP.
  if (kReleaseMode && !apiBaseUrl.startsWith('https://')) {
    throw StateError('Release builds require an https:// API_BASE_URL.');
  }
}
