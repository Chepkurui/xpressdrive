import '../api/api_client.dart';
import '../models/models.dart';

/// Towns, ports and border posts served. Loaded once per app run.
class Places {
  static List<Place>? _cache;
  static Future<List<Place>>? _loading;

  static Future<List<Place>> load(ApiClient api) {
    if (_cache != null) return Future.value(_cache);
    return _loading ??= api.get('/places/', auth: false).then((rows) {
      _cache = (rows as List).map((e) => Place.fromJson(e as Map<String, dynamic>)).toList()
        ..sort((a, b) => a.isBorder == b.isBorder ? 0 : (a.isBorder ? 1 : -1));
      return _cache!;
    }).whenComplete(() => _loading = null);
  }

  static String name(String code) =>
      _cache?.firstWhere((p) => p.code == code, orElse: () => Place.fromJson({'code': code, 'name': code})).name ?? code;
}
