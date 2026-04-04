import 'dart:convert';

import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'runtime/web_host_stub.dart' if (dart.library.html) 'runtime/web_host.dart' as web_host;

/// Baked in at build time (optional): `flutter build web --dart-define=API_BASE=https://api.example.com`
const String kApiBaseFromEnv = String.fromEnvironment('API_BASE', defaultValue: '');

const String _prefsKey = 'api_base_url';

String _normalize(String u) {
  var s = u.trim();
  if (s.isEmpty) return s;
  if (!s.startsWith('http://') && !s.startsWith('https://')) {
    s = 'http://$s';
  }
  if (s.endsWith('/')) {
    s = s.substring(0, s.length - 1);
  }
  return s;
}

bool _isLoopbackUrl(String u) {
  try {
    final h = Uri.parse(u).host.toLowerCase();
    return h == 'localhost' || h == '127.0.0.1' || h == '[::1]' || h == '::1';
  } catch (_) {
    return false;
  }
}

/// Default when no saved URL and no --dart-define (simulators / desktop).
String defaultApiBaseForPlatform() {
  if (kIsWeb) return 'http://127.0.0.1:8000';
  if (defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8000';
  }
  return 'http://127.0.0.1:8000';
}

/// Same-origin `web/api_config.json` — default local API in repo: http://127.0.0.1:8000
Future<String?> _tryWebApiConfigFile() async {
  if (!kIsWeb) return null;
  try {
    final baseUri = Uri.base.resolve('api_config.json');
    final uri = baseUri.replace(
      queryParameters: {
        ...baseUri.queryParameters,
        't': DateTime.now().millisecondsSinceEpoch.toString(),
      },
    );
    final r = await http.get(uri).timeout(const Duration(seconds: 12));
    if (r.statusCode != 200) return null;
    final dynamic j = jsonDecode(r.body);
    if (j is! Map) return null;
    final raw = j['apiBase'] ?? j['api_base'];
    if (raw == null) return null;
    final s = _normalize(raw.toString());
    return s.isEmpty ? null : s;
  } catch (_) {
    return null;
  }
}

Future<String> resolveApiBaseUrl() async {
  final env = _normalize(kApiBaseFromEnv);
  if (env.isNotEmpty) return env;

  final prefs = await SharedPreferences.getInstance();
  final savedRaw = prefs.getString(_prefsKey) ?? '';
  final saved = _normalize(savedRaw);

  final fromSite = await _tryWebApiConfigFile();

  if (kIsWeb) {
    final onPublicHost = web_host.isPublicWebHost();

    if (onPublicHost) {
      // Non-loopback HTTPS host: do not fall back to 127.0.0.1 from prefs or defaults.
      if (saved.isNotEmpty && !_isLoopbackUrl(saved)) return saved;
      if (fromSite != null) return fromSite;
      return '';
    }

    // Local web dev (localhost tab)
    if (saved.isNotEmpty && !_isLoopbackUrl(saved)) return saved;
    if (fromSite != null) return fromSite;
    if (saved.isNotEmpty) return saved;
    return defaultApiBaseForPlatform();
  }

  if (saved.isNotEmpty) return saved;
  if (fromSite != null) return fromSite;
  return defaultApiBaseForPlatform();
}

Future<void> saveApiBaseUrl(String url) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(_prefsKey, _normalize(url));
}

Future<void> clearSavedApiBaseUrl() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove(_prefsKey);
}
