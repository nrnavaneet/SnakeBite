import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../api_config.dart';
import '../theme/app_theme.dart';
import '../runtime/open_model_lab_stub.dart' if (dart.library.html) '../runtime/open_model_lab_web.dart' as model_lab;
import '../state/api_session.dart';
import '../widgets/tactile_pressable.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<ApiSession>();
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            elevation: 0,
            scrolledUnderElevation: 0,
            backgroundColor: AppTheme.surfaceElevated.withValues(alpha: 0.55),
            surfaceTintColor: Colors.transparent,
            toolbarHeight: 64,
            title: const Text('Settings'),
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(1),
              child: Divider(height: 1, thickness: 1, color: AppTheme.neon.withValues(alpha: 0.15)),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Text(
                  'API & device',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: cs.primary,
                      ),
                ),
                const SizedBox(height: 12),
                TactilePressable(
                  child: Card(
                    clipBehavior: Clip.antiAlias,
                    child: ListTile(
                      leading: Icon(Icons.dns_rounded, color: cs.primary),
                      title: const Text('Backend base URL'),
                      subtitle: Text(
                        session.baseUrl.isEmpty ? '(not configured)' : session.baseUrl,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12.5),
                      ),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => _openApiEditor(context),
                    ),
                  ),
                ).animate().fadeIn(duration: 350.ms).slideX(begin: -0.02),
                if (kIsWeb) ...[
                  const SizedBox(height: 12),
                  TactilePressable(
                    child: Card(
                      clipBehavior: Clip.antiAlias,
                      child: ListTile(
                        leading: Icon(Icons.science_outlined, color: cs.primary),
                        title: const Text('Model lab (atomic tests)'),
                        subtitle: const Text(
                          'Wound backbones, fusion, geo, symptoms, full /predict — opens lab.html',
                          style: TextStyle(fontSize: 12.5),
                        ),
                        trailing: const Icon(Icons.open_in_new_rounded),
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
                        color: cs.primary,
                      ),
                ),
                const SizedBox(height: 12),
                TactilePressable(
                  child: Card(
                    clipBehavior: Clip.antiAlias,
                    child: ListTile(
                      leading: Icon(Icons.gavel_rounded, color: cs.primary),
                      title: const Text('Disclaimer & limitations'),
                      subtitle: const Text('Educational use, model uncertainty, emergency guidance'),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () => _showLegal(context),
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  'Tip',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Text(
                  kIsWeb
                      ? 'Production: set "apiBase" in web/api_config.json (then redeploy), or set API_BASE in '
                        'Vercel. You can override below in this browser for testing. HTTPS only for real use.'
                      : 'On a physical phone, set the URL to your computer\'s LAN address, e.g. '
                        'http://192.168.1.10:8000, same Wi Fi as the dev machine. '
                        'Android emulator: 10.0.2.2:8000.',
                  style: TextStyle(height: 1.45, color: cs.onSurfaceVariant, fontSize: 14),
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
        title: const Text('API server'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Use your machine\'s IP and port where uvicorn runs (e.g. make api).',
                style: TextStyle(fontSize: 13, color: Theme.of(ctx).colorScheme.onSurfaceVariant, height: 1.4),
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
              Text('Legal & limitations', style: Theme.of(ctx).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 16),
              const Text(
                'SnakeBiteRx is educational software only. It is NOT a medical device and does NOT '
                'diagnose or treat snakebite. Models can make mistakes. Always follow local emergency protocols.',
                style: TextStyle(height: 1.5),
              ),
              const SizedBox(height: 16),
              Text(
                'Wound stack: EfficientNet-B3, ResNet50, DenseNet121 with softmax fusion (default 58% / 26% / 16%). '
                'Below 60% ensemble confidence the wound read is treated as uncertain and fusion leans on symptoms/geo.',
                style: TextStyle(height: 1.5, color: Theme.of(ctx).colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
