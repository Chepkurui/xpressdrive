import 'package:flutter/foundation.dart';

import '../api/api_client.dart';
import '../models/models.dart';

enum AuthState { unknown, signedOut, signedIn }

class AuthProvider extends ChangeNotifier {
  AuthProvider(this.api) {
    api.onAuthLost = () {
      user = null;
      state = AuthState.signedOut;
      notifyListeners();
    };
  }

  final ApiClient api;
  AuthState state = AuthState.unknown;
  AppUser? user;

  Future<void> restore() async {
    if (await api.refresh()) {
      try {
        await loadMe();
        state = AuthState.signedIn;
      } catch (_) {
        state = AuthState.signedOut;
      }
    } else {
      state = AuthState.signedOut;
    }
    notifyListeners();
  }

  Future<void> loadMe() async {
    user = AppUser.fromJson(await api.get('/auth/me/') as Map<String, dynamic>);
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    final data = await api.post('/auth/login/', body: {'email': email.trim(), 'password': password}, auth: false);
    await api.storeTokens(data as Map<String, dynamic>);
    await loadMe();
    state = AuthState.signedIn;
    notifyListeners();
  }

  Future<void> register(Map<String, String> payload) async {
    await api.post('/auth/register/', body: payload, auth: false);
    await login(payload['email']!, payload['password']!);
  }

  Future<void> updateProfile(Map<String, String> patch) async {
    user = AppUser.fromJson(await api.patch('/auth/me/', body: patch) as Map<String, dynamic>);
    notifyListeners();
  }

  Future<void> changePassword(String current, String next) async {
    await api.post('/auth/password/change/', body: {'current_password': current, 'new_password': next});
    await _signOutLocal();
  }

  /// Called on sign-out so a driver's phone stops sharing its location.
  Future<void> Function()? onSignOut;

  Future<void> logout() async {
    final refresh = await api.readRefresh();
    try {
      if (refresh != null) await api.post('/auth/logout/', body: {'refresh': refresh}, auth: false);
    } catch (_) {
      // Best effort: local tokens are wiped regardless.
    }
    await _signOutLocal();
  }

  Future<void> _signOutLocal() async {
    await onSignOut?.call();
    await api.clearTokens();
    user = null;
    state = AuthState.signedOut;
    notifyListeners();
  }
}
