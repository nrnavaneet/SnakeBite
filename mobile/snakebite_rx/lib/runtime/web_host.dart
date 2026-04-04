import 'package:web/web.dart' as web;

/// True when the app is opened from a normal HTTPS host (e.g. vercel.app), not localhost.
bool isPublicWebHost() {
  final h = web.window.location.hostname;
  if (h.isEmpty) return false;
  final lower = h.toLowerCase();
  return lower != 'localhost' && lower != '127.0.0.1' && lower != '::1';
}
