import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../theme/app_theme.dart';
import '../widgets/branding/app_logo.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar.large(
            title: const Text('How it works'),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 120),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Center(
                  child: AppLogo(size: 72, compact: true),
                ).animate().fadeIn(duration: 450.ms).scale(begin: const Offset(0.95, 0.95)),
                const SizedBox(height: 28),
                _Bullet(
                  icon: Icons.camera_enhance_rounded,
                  title: 'Wound vision',
                  body:
                      'Three CNN backbones score cytotoxic / neurotoxic / hemotoxic patterns. '
                      'Sharp, well-lit photos help. We only flag blur when quality is actually low.',
                ),
                _Bullet(
                  icon: Icons.monitor_heart_outlined,
                  title: 'Symptoms',
                  body:
                      'WHO-aligned symptom priors are fused with your selections and salience weighting.',
                ),
                _Bullet(
                  icon: Icons.map_rounded,
                  title: 'Geography',
                  body: 'Regional species priors adjust likelihoods for your country and state.',
                ),
                _Bullet(
                  icon: Icons.merge_rounded,
                  title: 'Fusion',
                  body:
                      'A multimodal blend produces a venom-type distribution, not a single diagnosis.',
                ),
                const SizedBox(height: 24),
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: cs.primary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.primary.withValues(alpha: 0.25)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Emergency', style: t.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
                      const SizedBox(height: 8),
                      Text(
                        'If someone is critically ill from a bite, call emergency services. '
                        'This app supports learning and triage awareness, not treatment decisions.',
                        style: TextStyle(height: 1.45, color: cs.onSurfaceVariant),
                      ),
                    ],
                  ),
                ).animate().fadeIn(delay: 200.ms),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bullet extends StatelessWidget {
  const _Bullet({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: cs.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: cs.primary, size: 26),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Text(body, style: TextStyle(height: 1.45, color: cs.onSurfaceVariant, fontSize: 14)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
