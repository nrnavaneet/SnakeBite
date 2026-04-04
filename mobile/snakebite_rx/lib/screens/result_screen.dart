import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../theme/app_theme.dart';
import '../widgets/ambient_background.dart';
import '../widgets/lab_parity_breakdown.dart';
import '../widgets/result_panel.dart';

/// Full-screen results with optional hero image. Blur overlay only when API flags bad quality.
class ResultScreen extends StatefulWidget {
  const ResultScreen({super.key, required this.result, this.imageBytes});

  final Map<String, dynamic> result;
  final Uint8List? imageBytes;

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  bool _devMode = false;

  @override
  Widget build(BuildContext context) {
    final result = widget.result;
    final imageBytes = widget.imageBytes;
    final cs = Theme.of(context).colorScheme;
    final iq = result['image_quality'];
    final badPhoto = iq is Map && iq['recommend_retake'] == true;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientBackground(
        child: CustomScrollView(
          slivers: [
            SliverAppBar(
              pinned: true,
              elevation: 0,
              scrolledUnderElevation: 0,
              backgroundColor: AppTheme.shellAppBarBackground,
              surfaceTintColor: Colors.transparent,
              toolbarHeight: 64,
              leading: IconButton(
                icon: const Icon(Icons.arrow_back_rounded),
                onPressed: () => Navigator.of(context).pop(),
              ),
              title: const Text(
                'Analysis',
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
              ),
              actions: [
                _AnalysisBreakdownToggle(
                  enabled: _devMode,
                  onToggle: () => setState(() => _devMode = !_devMode),
                ),
              ],
              bottom: PreferredSize(
                preferredSize: const Size.fromHeight(1),
                child: Divider(height: 1, thickness: 1, color: AppTheme.neon.withValues(alpha: 0.15)),
              ),
            ),
          if (imageBytes != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final mq = MediaQuery.sizeOf(context);
                    final h = (mq.height * 0.22).clamp(160.0, 240.0);
                    final w = math.min(constraints.maxWidth, 420.0);
                    return Align(
                      alignment: Alignment.center,
                      child: Hero(
                        tag: 'wound_photo',
                        child: Material(
                          color: Colors.transparent,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(20),
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                color: cs.surfaceContainerHighest.withValues(alpha: 0.45),
                                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
                              ),
                              child: SizedBox(
                                width: w,
                                height: h,
                                child: Stack(
                                  fit: StackFit.expand,
                                  children: [
                                    badPhoto
                                        ? ImageFiltered(
                                            imageFilter: ImageFilter.blur(sigmaX: 9, sigmaY: 9),
                                            child: Image.memory(
                                              imageBytes,
                                              fit: BoxFit.contain,
                                              alignment: Alignment.center,
                                            ),
                                          )
                                        : Image.memory(
                                            imageBytes,
                                            fit: BoxFit.contain,
                                            alignment: Alignment.center,
                                            gaplessPlayback: true,
                                          ),
                                    if (badPhoto)
                                      Container(
                                        color: Colors.black.withValues(alpha: 0.35),
                                        alignment: Alignment.center,
                                        child: Container(
                                          margin: const EdgeInsets.all(16),
                                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                          decoration: BoxDecoration(
                                            color: cs.surface.withValues(alpha: 0.92),
                                            borderRadius: BorderRadius.circular(14),
                                          ),
                                          child: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              Icon(Icons.photo_camera_rounded, color: cs.primary, size: 22),
                                              const SizedBox(width: 8),
                                              Flexible(
                                                child: Text(
                                                  'Blur preview. Retake for a sharper photo',
                                                  style: TextStyle(
                                                    fontWeight: FontWeight.w700,
                                                    fontSize: 13,
                                                    color: cs.onSurface,
                                                  ),
                                                  textAlign: TextAlign.center,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ).animate().fadeIn(duration: 400.ms).scale(begin: const Offset(0.97, 0.97), curve: Curves.easeOutCubic),
              ),
            ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 40),
            sliver: SliverToBoxAdapter(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ResultPanel(result: result, devMode: _devMode),
                  if (_devMode) ...[
                    const Divider(height: 36, thickness: 1),
                    LabParityBreakdown(result: result),
                  ],
                ],
              ),
            ),
          ),
        ],
        ),
      ),
    );
  }
}

/// App bar control: show fused summary vs full per-model / atomic breakdown (not the generic “developer” glyph).
class _AnalysisBreakdownToggle extends StatelessWidget {
  const _AnalysisBreakdownToggle({
    required this.enabled,
    required this.onToggle,
  });

  final bool enabled;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final narrow = MediaQuery.sizeOf(context).width < 380;
    final label = enabled ? 'Less' : 'Breakdown';
    final tooltip = enabled
        ? 'Hide model breakdown (wound / symptom / geo vectors)'
        : 'Show model breakdown — per-modality distributions & lab parity';

    const accent = AppTheme.neon;
    final borderColor = enabled ? accent.withValues(alpha: 0.55) : cs.outlineVariant.withValues(alpha: 0.38);
    final bg = enabled ? accent.withValues(alpha: 0.12) : cs.surfaceContainerHighest.withValues(alpha: 0.4);

    final child = Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(22),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          padding: EdgeInsets.symmetric(horizontal: narrow ? 10 : 12, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: borderColor, width: enabled ? 1.5 : 1),
            color: bg,
            boxShadow: enabled
                ? [
                    BoxShadow(
                      color: accent.withValues(alpha: 0.18),
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: narrow
              ? Icon(
                  Icons.account_tree_rounded,
                  size: 22,
                  color: enabled ? accent : cs.onSurfaceVariant,
                )
              : Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.account_tree_rounded,
                      size: 18,
                      color: enabled ? accent : cs.onSurfaceVariant,
                    ),
                    const SizedBox(width: 7),
                    Text(
                      label,
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.35,
                        color: enabled ? accent : cs.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );

    return Padding(
      padding: const EdgeInsets.only(right: 6, top: 10, bottom: 10),
      child: Tooltip(
        message: tooltip,
        child: child,
      ),
    );
  }
}
