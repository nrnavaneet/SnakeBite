import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../theme/app_theme.dart';
import '../theme/breakpoints.dart';
import '../widgets/branding/app_logo.dart';
import '../widgets/shell_menu_leading.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
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
              'How it works',
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
                    color: const Color(0xFF151C28),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: AppTheme.neon.withValues(alpha: 0.45)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.35),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Emergency',
                        style: t.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                          color: AppTheme.ink,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'If someone is critically ill from a bite, call emergency services. '
                        'This app supports learning and triage awareness, not treatment decisions.',
                        style: TextStyle(
                          height: 1.5,
                          fontSize: 14.5,
                          color: AppTheme.ink.withValues(alpha: 0.92),
                          fontWeight: FontWeight.w500,
                        ),
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
    final narrow = MediaQuery.sizeOf(context).width < 400;
    final iconBox = Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.neon.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.neon.withValues(alpha: 0.28)),
      ),
      child: Icon(icon, color: AppTheme.neon, size: 26),
    );
    final textCol = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w800,
                color: AppTheme.ink,
                letterSpacing: -0.2,
              ),
        ),
        const SizedBox(height: 8),
        Text(
          body,
          style: TextStyle(
            height: 1.5,
            fontSize: 14.5,
            color: AppTheme.ink.withValues(alpha: 0.88),
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xFF121924),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.25),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: narrow
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    iconBox,
                    const SizedBox(height: 14),
                    textCol,
                  ],
                )
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    iconBox,
                    const SizedBox(width: 14),
                    Expanded(child: textCol),
                  ],
                ),
        ),
      ),
    );
  }
}
