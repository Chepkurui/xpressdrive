import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.status, this.data);
  final int status;
  final dynamic data;

  String get message {
    final d = data;
    if (d is Map) {
      if (d['detail'] != null) return d['detail'].toString();
      if (d.isNotEmpty) {
        final entry = d.entries.first;
        final v = entry.value is List ? (entry.value as List).join(' ') : entry.value.toString();
        return entry.key == 'non_field_errors' ? v : '${entry.key.toString().replaceAll('_', ' ')}: $v';
      }
    }
    if (status == 0) return 'Network error. Check your connection and try again.';
    if (status == 429) return 'Too many requests. Please wait a moment and try again.';
    return 'Something went wrong ($status).';
  }

  String? field(String name) {
    final v = (data is Map) ? data[name] : null;
    if (v == null) return null;
    return v is List ? v.join(' ') : v.toString();
  }

  @override
  String toString() => message;
}

/// HTTP client for the XpressDrive API.
///
/// Access token: memory only. Refresh token: platform secure storage
/// (Keychain / Android Keystore). Refresh tokens rotate on every use.
class ApiClient {
  ApiClient({required String baseUrl, FlutterSecureStorage? storage, http.Client? client})
      : _base = baseUrl.replaceAll(RegExp(r'/$'), ''),
        _storage = storage ?? const FlutterSecureStorage(),
        _http = client ?? http.Client();

  static const _refreshKey = 'xd_refresh_token';
  static const _timeout = Duration(seconds: 20);

  final String _base;
  final FlutterSecureStorage _storage;
  final http.Client _http;
  String? _access;
  Future<bool>? _refreshing;
  void Function()? onAuthLost;

  bool get hasSession => _access != null;

  Map<String, String> _headers({bool json = false, bool auth = true}) => {
        'Accept': 'application/json',
        'X-Client': 'mobile',
        if (json) 'Content-Type': 'application/json',
        if (auth && _access != null) 'Authorization': 'Bearer $_access',
      };

  Uri _uri(String path, [Map<String, String>? query]) {
    final q = query == null ? null : (Map.of(query)..removeWhere((_, v) => v.isEmpty));
    return Uri.parse('$_base/api$path').replace(queryParameters: (q == null || q.isEmpty) ? null : q);
  }

  Future<void> storeTokens(Map<String, dynamic> data) async {
    _access = data['access'] as String?;
    final refresh = data['refresh'] as String?;
    if (refresh != null) await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clearTokens() async {
    _access = null;
    await _storage.delete(key: _refreshKey);
  }

  Future<String?> readRefresh() => _storage.read(key: _refreshKey);

  Future<bool> refresh() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<bool> _doRefresh() async {
    final token = await readRefresh();
    if (token == null) return false;
    try {
      final res = await _http
          .post(_uri('/auth/refresh/'), headers: _headers(json: true, auth: false), body: jsonEncode({'refresh': token}))
          .timeout(_timeout);
      if (res.statusCode != 200) {
        if (res.statusCode == 401) await clearTokens();
        return false;
      }
      await storeTokens(jsonDecode(res.body) as Map<String, dynamic>);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<dynamic> get(String path, {Map<String, String>? query, bool auth = true}) =>
      _send('GET', path, query: query, auth: auth);
  Future<dynamic> post(String path, {Object? body, bool auth = true}) => _send('POST', path, body: body, auth: auth);
  Future<dynamic> patch(String path, {Object? body}) => _send('PATCH', path, body: body);
  Future<dynamic> delete(String path) => _send('DELETE', path);

  Future<dynamic> _send(String method, String path,
      {Object? body, Map<String, String>? query, bool auth = true, bool retry = true}) async {
    final req = http.Request(method, _uri(path, query))..headers.addAll(_headers(json: body != null, auth: auth));
    if (body != null) req.body = jsonEncode(body);

    http.Response res;
    try {
      res = await http.Response.fromStream(await _http.send(req).timeout(_timeout));
    } on TimeoutException {
      throw ApiException(0, null);
    } catch (_) {
      throw ApiException(0, null);
    }

    if (res.statusCode == 401 && auth && retry) {
      if (await refresh()) return _send(method, path, body: body, query: query, auth: auth, retry: false);
      await clearTokens();
      onAuthLost?.call();
    }
    if (res.statusCode == 204 || res.body.isEmpty) {
      if (res.statusCode >= 400) throw ApiException(res.statusCode, null);
      return null;
    }
    dynamic data;
    try {
      data = jsonDecode(utf8.decode(res.bodyBytes));
    } catch (_) {
      data = null;
    }
    if (res.statusCode >= 400) throw ApiException(res.statusCode, data);
    return data;
  }
}
