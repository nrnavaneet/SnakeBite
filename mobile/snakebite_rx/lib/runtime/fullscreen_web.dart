// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter
// Web-only fullscreen; dart:html is the stable interop for this call site.
import 'dart:html' as html;

/// Browser fullscreen (user gesture required). iOS in-tab: limited; use “Add to Home Screen” for chromeless PWA.
Future<void> requestWebFullscreen() async {
  final el = html.document.documentElement;
  if (el == null) return;
  try {
    await el.requestFullscreen();
  } catch (_) {
    try {
      await html.document.body?.requestFullscreen();
    } catch (_) {}
  }
}

Future<void> exitWebFullscreen() async {
  try {
    html.document.exitFullscreen();
  } catch (_) {}
}

bool get webFullscreenApiSupported => html.document.documentElement != null;
