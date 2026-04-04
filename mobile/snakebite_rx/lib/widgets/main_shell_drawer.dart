import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Left drawer for mobile: same destinations as bottom NavigationBar.
class MainShellDrawer extends StatelessWidget {
  const MainShellDrawer({
    super.key,
    required this.selectedIndex,
    required this.onDestinationSelected,
  });

  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  static const _items = <({IconData icon, IconData iconSel, String label})>[
    (icon: Icons.biotech_outlined, iconSel: Icons.biotech_rounded, label: 'Assess'),
    (icon: Icons.menu_book_outlined, iconSel: Icons.menu_book_rounded, label: 'Guide'),
    (icon: Icons.tune_outlined, iconSel: Icons.tune_rounded, label: 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Drawer(
      backgroundColor: AppTheme.shellAppBarBackground,
      surfaceTintColor: Colors.transparent,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Material(
              color: AppTheme.surfaceElevated,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 16, 12),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(14),
                        gradient: const LinearGradient(
                          colors: [AppTheme.primary, AppTheme.primaryDark],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.primaryDark.withValues(alpha: 0.35),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: const Icon(Icons.healing_rounded, color: AppTheme.void_, size: 24),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'SnakeBiteRx',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: -0.4,
                                  color: AppTheme.ink,
                                ),
                          ),
                          Text(
                            'Navigation',
                            style: TextStyle(
                              fontSize: 12,
                              color: cs.onSurfaceVariant,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Divider(height: 1, thickness: 1, color: AppTheme.neon.withValues(alpha: 0.15)),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.only(top: 8),
                children: [
                  for (var i = 0; i < _items.length; i++)
                    ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      selected: selectedIndex == i,
                      selectedTileColor: AppTheme.neon.withValues(alpha: 0.12),
                      leading: Icon(
                        selectedIndex == i ? _items[i].iconSel : _items[i].icon,
                        color: selectedIndex == i ? AppTheme.neon : cs.onSurfaceVariant,
                      ),
                      title: Text(
                        _items[i].label,
                        style: TextStyle(
                          fontWeight: selectedIndex == i ? FontWeight.w800 : FontWeight.w600,
                          color: selectedIndex == i ? AppTheme.neon : cs.onSurface,
                        ),
                      ),
                      onTap: () {
                        onDestinationSelected(i);
                        Navigator.of(context).pop();
                      },
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Text(
                'Educational software only — not a medical device.',
                style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant, height: 1.35),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
