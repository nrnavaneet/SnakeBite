import 'package:flutter/material.dart';

/// Below this width: hamburger + drawer, no bottom nav (mobile web / phones).
const double kShellCompactWidth = 600;

bool isShellCompactWidth(BuildContext context) {
  return MediaQuery.sizeOf(context).width < kShellCompactWidth;
}

/// Space under scroll content: large when bottom nav is shown, small on mobile.
double shellScrollBottomPadding(BuildContext context) {
  final pad = MediaQuery.paddingOf(context).bottom;
  if (isShellCompactWidth(context)) {
    return 16 + pad;
  }
  return 120;
}

double shellPageHorizontalPadding(BuildContext context) {
  return isShellCompactWidth(context) ? 14.0 : 20.0;
}
