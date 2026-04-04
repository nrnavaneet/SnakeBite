import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

/// Vector wordmark + icon. No raster assets required (swap in Image.asset later).
class AppLogo extends StatelessWidget {
  const AppLogo({super.key, this.size = 120, this.compact = false});

  final double size;
  /// Single-line small header variant.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _Mark(side: size * 0.36),
          const SizedBox(width: 10),
          Text(
            'SnakeBiteRx',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.6,
                  color: AppTheme.primaryDark,
                ),
          ),
        ],
      );
    }
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        _Mark(side: size),
        const SizedBox(height: 16),
        Text(
          'SnakeBiteRx',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: -0.8,
                color: AppTheme.primaryDark,
              ),
        ),
        const SizedBox(height: 6),
        Text(
          'Clinical decision support · educational',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
                fontWeight: FontWeight.w500,
              ),
        ),
      ],
    );
  }
}

class _Mark extends StatelessWidget {
  const _Mark({required this.side});

  final double side;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: side,
      height: side,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(side * 0.22),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF14B8A6), AppTheme.primaryDark],
        ),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryDark.withValues(alpha: 0.35),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(side * 0.72, side * 0.72),
            painter: _SnakeCurvePainter(color: Colors.white.withValues(alpha: 0.92)),
          ),
          Icon(Icons.medical_services_rounded, color: Colors.white, size: side * 0.38),
        ],
      ),
    );
  }
}

class _SnakeCurvePainter extends CustomPainter {
  _SnakeCurvePainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..color = color.withValues(alpha: 0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.shortestSide * 0.08
      ..strokeCap = StrokeCap.round;

    final path = Path();
    final w = size.width;
    final h = size.height;
    path.moveTo(w * 0.1, h * 0.55);
    for (var i = 0; i < 4; i++) {
      final t = i / 3;
      final x = w * (0.15 + t * 0.7);
      final y = h * (0.5 + 0.12 * math.sin(t * math.pi * 2));
      path.lineTo(x, y);
    }
    canvas.drawPath(path, p);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
