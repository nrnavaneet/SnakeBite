/// Not web — no browser fullscreen API.
Future<void> requestWebFullscreen() async {}

Future<void> exitWebFullscreen() async {}

bool get webFullscreenApiSupported => false;
