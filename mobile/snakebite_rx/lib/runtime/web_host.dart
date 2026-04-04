import 'package:web/web.dart' as web;

/// True when the app is opened from a non-loopback HTTPS host (not localhost file/dev).
bool isPublicWebHost() {
  final h = web.window.location.hostname;
  if (h.isEmpty) return false;
  final lower = h.toLowerCase();
  return lower != 'localhost' && lower != '127.0.0.1' && lower != '::1';
}
