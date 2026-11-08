import 'package:flutter/material.dart';

const navy = Color(0xFF0F2A44);
const amber = Color(0xFFFF8A1F);
const amberDark = Color(0xFFC45F00);
/// Page background, shared by every tab screen and the bottom bar.
const canvas = Color(0xFFF4F6F9);

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: navy, primary: navy, secondary: amber);
  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    scaffoldBackgroundColor: canvas,
    appBarTheme: const AppBarTheme(backgroundColor: navy, foregroundColor: Colors.white),
    // Bottom bar sits on the same background as the screens, orange marks the current tab.
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: canvas,
      surfaceTintColor: Colors.transparent,
      indicatorColor: amber,
      iconTheme: WidgetStateProperty.resolveWith((s) => IconThemeData(color: s.contains(WidgetState.selected) ? navy : const Color(0xFF5B6878))),
      labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
            fontSize: 12,
            color: s.contains(WidgetState.selected) ? navy : const Color(0xFF5B6878),
            fontWeight: s.contains(WidgetState.selected) ? FontWeight.w600 : FontWeight.w500,
          )),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: Color(0xFFE0E6EE), width: 2)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
    ),
  );
}
