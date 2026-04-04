import 'package:flutter/foundation.dart';

import '../api_config.dart';

/// Shared API base URL + bootstrap flag for assess + settings.
class ApiSession extends ChangeNotifier {
  ApiSession() {
    _base = defaultApiBaseForPlatform();
  }

  String _base = defaultApiBaseForPlatform();
  bool _ready = false;

  String get baseUrl => _base;
  bool get isReady => _ready;

  Future<void> resolve() async {
    _base = await resolveApiBaseUrl();
    _ready = true;
    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    await saveApiBaseUrl(url);
    await resolve();
  }

  Future<void> clearSaved() async {
    await clearSavedApiBaseUrl();
    await resolve();
  }
}
