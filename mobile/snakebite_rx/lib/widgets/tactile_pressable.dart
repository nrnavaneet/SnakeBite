import 'package:flutter/material.dart';

/// Light press feedback (tiny scale) for rows and cards. Does not replace ink/splash on children.
class TactilePressable extends StatefulWidget {
  const TactilePressable({
    super.key,
    required this.child,
    this.scale = 0.992,
    this.duration = const Duration(milliseconds: 105),
  });

  final Widget child;
  final double scale;
  final Duration duration;

  @override
  State<TactilePressable> createState() => _TactilePressableState();
}

class _TactilePressableState extends State<TactilePressable> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: (_) => setState(() => _pressed = true),
      onPointerUp: (_) => setState(() => _pressed = false),
      onPointerCancel: (_) => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? widget.scale : 1,
        duration: widget.duration,
        curve: Curves.easeOutCubic,
        child: widget.child,
      ),
    );
  }
}
