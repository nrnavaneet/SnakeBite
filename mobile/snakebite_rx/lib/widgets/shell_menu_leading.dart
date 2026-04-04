import 'package:flutter/material.dart';

import '../theme/breakpoints.dart';

/// Hamburger that opens [MainShell] drawer. Use as [SliverAppBar.leading] on narrow layouts only.
Widget? shellMenuLeadingButton(BuildContext context) {
  if (!isShellCompactWidth(context)) {
    return null;
  }
  return IconButton(
    icon: const Icon(Icons.menu_rounded),
    tooltip: 'Menu',
    onPressed: () => Scaffold.of(context).openDrawer(),
  );
}
