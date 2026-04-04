import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Layered glow orbs + mesh for a hyper-real depth field (static, GPU-friendly).
class AmbientBackground extends StatefulWidget {
  const AmbientBackground({super.key, required this.child});

  final Widget child;

  @override
  State<AmbientBackground> createState() => _AmbientBackgroundState();
}

class _AmbientBackgroundState extends State<AmbientBackground> with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(seconds: 14))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final t = CurvedAnimation(parent: _c, curve: Curves.easeInOutCubic).value;
        final drift = t * 0.04;
        return Stack(
          fit: StackFit.expand,
          children: [
            DecoratedBox(decoration: BoxDecoration(gradient: AppTheme.scaffoldGradient)),
            Positioned(
              top: -120 + drift * 40,
              right: -80 - drift * 30,
              child: _GlowBlob(
                diameter: 280,
                color: AppTheme.neon.withValues(alpha: 0.45),
                blur: 100,
              ),
            ),
            Positioned(
              bottom: 80 - drift * 20,
              left: -100 + drift * 25,
              child: _GlowBlob(
                diameter: 320,
                color: AppTheme.violet.withValues(alpha: 0.35),
                blur: 110,
              ),
            ),
            Positioned(
              top: math.min(MediaQuery.sizeOf(context).height * 0.35, 400),
              left: MediaQuery.sizeOf(context).width * 0.2 + drift * 15,
              child: _GlowBlob(
                diameter: 180,
                color: AppTheme.rose.withValues(alpha: 0.18),
                blur: 80,
              ),
            ),
            widget.child,
          ],
        );
      },
    );
  }
}

class _GlowBlob extends StatelessWidget {
  const _GlowBlob({required this.diameter, required this.color, required this.blur});

  final double diameter;
  final Color color;
  final double blur;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: diameter,
        height: diameter,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(color: color, blurRadius: blur, spreadRadius: 20),
          ],
        ),
      ),
    );
  }
}
