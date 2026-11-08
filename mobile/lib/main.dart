import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'config.dart';
import 'screens/driver/driver_shell.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';
import 'state/auth_provider.dart';
import 'state/location_service.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  assertSecureConfig();
  final api = ApiClient(baseUrl: apiBaseUrl);
  final location = LocationService(api);
  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<LocationService>.value(value: location),
        ChangeNotifierProvider(create: (_) => AuthProvider(api)
          ..onSignOut = (() => location.stop())
          ..restore()),
      ],
      child: const XpressDriveApp(),
    ),
  );
}

class XpressDriveApp extends StatelessWidget {
  const XpressDriveApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'XpressDrive',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: Consumer<AuthProvider>(
        builder: (context, auth, _) => switch (auth.state) {
          AuthState.unknown => const Scaffold(body: Center(child: CircularProgressIndicator())),
          AuthState.signedOut => const LoginScreen(),
          // Drivers get the driver app; everyone else books and tracks cargo.
          AuthState.signedIn => auth.user?.canDrive == true ? const DriverShell() : const HomeShell(),
        },
      ),
    );
  }
}
