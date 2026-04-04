import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';

import '../theme/app_theme.dart';
import '../widgets/branding/app_logo.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>(() async {
      await Future<void>.delayed(const Duration(milliseconds: 2200));
      if (!mounted) return;
      context.go('/home');
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFE0F2FE),
              AppTheme.surface,
              Color(0xFFF0FDFA),
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const Spacer(flex: 2),
              const AppLogo(size: 112)
                  .animate()
                  .fadeIn(duration: 600.ms, curve: Curves.easeOut)
                  .scale(begin: const Offset(0.88, 0.88), duration: 700.ms, curve: Curves.easeOutCubic),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  'Multimodal venom-type estimation from wound imaging, symptoms, and geography '
                  'for training and research contexts only.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    height: 1.45,
                    color: cs.onSurfaceVariant,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              )
                  .animate(delay: 400.ms)
                  .fadeIn(duration: 500.ms)
                  .slideY(begin: 0.08, duration: 500.ms, curve: Curves.easeOutCubic),
              const SizedBox(height: 36),
              SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: cs.primary,
                ),
              ).animate().fadeIn(delay: 800.ms),
              const Spacer(flex: 2),
              Text(
                'Not a medical device',
                style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant.withValues(alpha: 0.85)),
              ).animate().fadeIn(delay: 1200.ms),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
