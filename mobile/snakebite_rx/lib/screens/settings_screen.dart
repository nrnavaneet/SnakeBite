import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../api_config.dart';
import '../theme/app_theme.dart';
import '../theme/breakpoints.dart';
import '../widgets/shell_menu_leading.dart';
import '../runtime/open_model_lab_stub.dart' if (dart.library.html) '../runtime/open_model_lab_web.dart' as model_lab;
import '../runtime/fullscreen_stub.dart' if (dart.library.html) '../runtime/fullscreen_web.dart' as fullscreen;
import '../state/api_session.dart';
import '../widgets/tactile_pressable.dart';

/// Dark card + readable ListTile text on the HUD background.
Widget _settingsCard(BuildContext context, {required Widget child}) {
  return Theme(
    data: Theme.of(context).copyWith(
      listTileTheme: ListTileThemeData(
        titleTextStyle: const TextStyle(
          color: AppTheme.ink,
          fontWeight: FontWeight.w700,
          fontSize: 16,
          height: 1.25,
        ),
        subtitleTextStyle: TextStyle(
          color: AppTheme.ink.withValues(alpha: 0.78),
          fontSize: 13,
          height: 1.4,
        ),
      ),
    ),
    child: Card(
      clipBehavior: Clip.antiAlias,
      color: const Color(0xFF121924),
      shadowColor: Colors.black.withValues(alpha: 0.4),
      child: child,
    ),
  );
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<ApiSession>();
    final gx = shellPageHorizontalPadding(context);
    final gb = shellScrollBottomPadding(context);

    return Material(
      color: Colors.transparent,
      child: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            elevation: 0,
            scrolledUnderElevation: 0,
            backgroundColor: AppTheme.shellAppBarBackground,
            surfaceTintColor: Colors.transparent,
            toolbarHeight: 64,
            automaticallyImplyLeading: false,
            leading: shellMenuLeadingButton(context),
            title: Text(
              'Settings',
              style: Theme.of(context).appBarTheme.titleTextStyle?.copyWith(
                    color: AppTheme.ink,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(1),
              child: Divider(height: 1, thickness: 1, color: AppTheme.neon.withValues(alpha: 0.15)),
            ),
          ),
          SliverPadding(
            padding: EdgeInsets.fromLTRB(gx, 12, gx, gb),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Text(
                  'API & device',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: AppTheme.neon,
                      ),
                ),
                const SizedBox(height: 12),
                TactilePressable(
                  child: _settingsCard(
                    context,
                    child: ListTile(
                      leading: Icon(Icons.dns_rounded, color: AppTheme.neon),
                      title: const Text('Backend base URL'),
                      subtitle: Text(
                        session.baseUrl.isEmpty ? '(not configured)' : session.baseUrl,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: Icon(Icons.chevron_right_rounded, color: AppTheme.ink.withValues(alpha: 0.5)),
                      onTap: () => _openApiEditor(context),
                    ),
                  ),
                ).animate().fadeIn(duration: 350.ms).slideX(begin: -0.02),
                if (kIsWeb) ...[
                  const SizedBox(height: 12),
                  TactilePressable(
                    child: _settingsCard(
                      context,
                      child: ListTile(
                        leading: Icon(Icons.fullscreen_rounded, color: AppTheme.neon),
                        title: const Text('Full screen'),
                        subtitle: const Text(
                          'Hides browser toolbars (Chrome / Edge / Android). iOS Safari: use Share → Add to Home Screen for an app-style, chromeless window.',
                        ),
                        trailing: Icon(Icons.chevron_right_rounded, color: AppTheme.ink.withValues(alpha: 0.5)),
                        onTap: () => fullscreen.requestWebFullscreen(),
                      ),
                    ),
                  ).animate().fadeIn(duration: 350.ms).slideX(begin: -0.02),
                  const SizedBox(height: 12),
                  TactilePressable(
                    child: _settingsCard(
                      context,
                      child: ListTile(
                        leading: Icon(Icons.science_outlined, color: AppTheme.neon),
                        title: const Text('Model lab (atomic tests)'),
                        subtitle: const Text(
                          'Wound backbones, fusion, geo, symptoms, full /predict — opens lab.html',
                        ),
                        trailing: Icon(Icons.open_in_new_rounded, color: AppTheme.ink.withValues(alpha: 0.5)),
                        onTap: () => model_lab.openModelLab(context, session.baseUrl),
                      ),
                    ),
                  ).animate().fadeIn(duration: 350.ms).slideX(begin: -0.02),
                ],
                const SizedBox(height: 20),
                Text(
                  'Legal',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: AppTheme.neon,
                      ),
                ),
                const SizedBox(height: 12),
                TactilePressable(
                  child: _settingsCard(
                    context,
                    child: ListTile(
                      leading: Icon(Icons.gavel_rounded, color: AppTheme.neon),
                      title: const Text('Disclaimer & limitations'),
                      subtitle: const Text('Educational use, model uncertainty, emergency guidance'),
                      trailing: Icon(Icons.chevron_right_rounded, color: AppTheme.ink.withValues(alpha: 0.5)),
                      onTap: () => _showLegal(context),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF161E2E),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.neon.withValues(alpha: 0.28)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Tip',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                              color: AppTheme.neon,
                            ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        kIsWeb
                            ? 'Local default is http://127.0.0.1:8000 (see web/api_config.json). Change Backend base URL above if the API runs elsewhere (tunnel, LAN IP, etc.).'
                            : 'On a physical phone, set the URL to your computer\'s LAN address, e.g. '
                                'http://192.168.1.10:8000, same Wi‑Fi as the dev machine. '
                                'Android emulator: http://10.0.2.2:8000',
                        style: TextStyle(
                          height: 1.5,
                          fontSize: 14,
                          color: AppTheme.ink.withValues(alpha: 0.92),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  static Future<void> _openApiEditor(BuildContext context) async {
    final session = context.read<ApiSession>();
    final controller = TextEditingController(text: session.baseUrl);
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A2332),
        title: Text('API server', style: TextStyle(color: AppTheme.ink, fontWeight: FontWeight.w800)),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Use your machine\'s IP and port where uvicorn runs (e.g. make api).',
                style: TextStyle(fontSize: 13, color: AppTheme.ink.withValues(alpha: 0.88), height: 1.4),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                decoration: const InputDecoration(
                  labelText: 'Base URL',
                  hintText: 'http://192.168.0.5:8000',
                ),
                keyboardType: TextInputType.url,
                autocorrect: false,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              await session.clearSaved();
              controller.text = defaultApiBaseForPlatform();
            },
            child: const Text('Clear saved'),
          ),
          FilledButton(
            onPressed: () async {
              await session.setBaseUrl(controller.text);
              if (!ctx.mounted) return;
              Navigator.of(ctx).pop();
              if (!context.mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Saved. Reopen the Assess tab if lists do not refresh.')),
              );
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  static Future<void> _showLegal(BuildContext context) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: const Color(0xFF141B26),
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.72,
        maxChildSize: 0.95,
        minChildSize: 0.4,
        builder: (_, scroll) => Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: ListView(
            controller: scroll,
            children: [
              Text(
                'Legal & limitations',
                style: Theme.of(ctx).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: AppTheme.ink,
                    ),
              ),
              const SizedBox(height: 16),
              Text(
                'SnakeBiteRx is educational software only. It is NOT a medical device and does NOT '
                'diagnose or treat snakebite. Models can make mistakes. Always follow local emergency protocols.',
                style: TextStyle(height: 1.5, color: AppTheme.ink.withValues(alpha: 0.92)),
              ),
              const SizedBox(height: 16),
              Text(
                'Wound stack: EfficientNet-B3, ResNet50, DenseNet121 with softmax fusion (default 58% / 26% / 16%). '
                'Below 60% ensemble confidence the wound read is treated as uncertain and fusion leans on symptoms/geo.',
                style: TextStyle(height: 1.5, color: AppTheme.ink.withValues(alpha: 0.78)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
