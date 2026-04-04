import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/breakpoints.dart';
import '../widgets/ambient_background.dart';
import '../widgets/main_shell_drawer.dart';
import 'about_screen.dart';
import 'assess_screen.dart';
import 'settings_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pad = MediaQuery.paddingOf(context);
    final compact = isShellCompactWidth(context);
    return AmbientBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        extendBody: true,
        drawer: compact
            ? MainShellDrawer(
                selectedIndex: _index,
                onDestinationSelected: (i) => setState(() => _index = i),
              )
            : null,
        body: AnimatedSwitcher(
          duration: const Duration(milliseconds: 520),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          transitionBuilder: (child, anim) {
            final curved = CurvedAnimation(parent: anim, curve: Curves.easeOutCubic);
            return FadeTransition(
              opacity: curved,
              child: ScaleTransition(
                scale: Tween<double>(begin: 0.97, end: 1).animate(curved),
                child: SlideTransition(
                  position: Tween<Offset>(begin: const Offset(0.04, 0.015), end: Offset.zero).animate(curved),
                  child: child,
                ),
              ),
            );
          },
          child: KeyedSubtree(
            key: ValueKey<int>(_index),
            child: switch (_index) {
              0 => const AssessScreen(),
              1 => const AboutScreen(),
              _ => const SettingsScreen(),
            },
          ),
        ),
        bottomNavigationBar: compact
            ? null
            : Padding(
                padding: EdgeInsets.only(
                  left: 14,
                  right: 14,
                  bottom: pad.bottom > 0 ? pad.bottom + 6 : 14,
                  top: 8,
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(28),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(28),
                        color: AppTheme.shellNavBarBackground,
                        border: Border.all(color: AppTheme.neon.withValues(alpha: 0.22)),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.neon.withValues(alpha: 0.12),
                            blurRadius: 36,
                            offset: const Offset(0, 14),
                          ),
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.5),
                            blurRadius: 24,
                            offset: const Offset(0, 12),
                          ),
                        ],
                      ),
                      child: NavigationBar(
                        height: 66,
                        backgroundColor: Colors.transparent,
                        selectedIndex: _index,
                        onDestinationSelected: (i) => setState(() => _index = i),
                        animationDuration: const Duration(milliseconds: 450),
                        destinations: const [
                          NavigationDestination(
                            icon: Icon(Icons.biotech_outlined),
                            selectedIcon: Icon(Icons.biotech_rounded),
                            label: 'Assess',
                          ),
                          NavigationDestination(
                            icon: Icon(Icons.menu_book_outlined),
                            selectedIcon: Icon(Icons.menu_book_rounded),
                            label: 'Guide',
                          ),
                          NavigationDestination(
                            icon: Icon(Icons.tune_outlined),
                            selectedIcon: Icon(Icons.tune_rounded),
                            label: 'Settings',
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
      ),
    );
  }
}
