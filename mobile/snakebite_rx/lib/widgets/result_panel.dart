import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../theme/app_theme.dart';

class ResultPanel extends StatelessWidget {
  const ResultPanel({super.key, required this.result, this.compact = false, this.devMode = false});

  final Map<String, dynamic> result;
  final bool compact;

  /// When true, show full multimodal breakdown, distributions, wound branch, etc.
  /// When false (default), show fused top class + likely snakes and safety banners only.
  final bool devMode;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final iq = result['image_quality'];
    final retake = iq is Map && iq['recommend_retake'] == true;
    final severeBlur = iq is Map && iq['severe_blur'] == true;
    final displayTop =
        (result['display_top_class'] ?? result['top_class'])?.toString() ?? '';
    final conf = (result['top_confidence'] as num?)?.toDouble() ?? 0;
    final predictionUncertain = result['prediction_uncertain'] == true;
    final classes = (result['classes'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final probs = (result['final_probability'] as List?)?.map((e) => (e as num).toDouble()).toList() ?? [];
    final snakes = (result['snake_species_top'] as List?) ?? [];
    final ranked = (result['selected_symptoms_ranked'] as List?) ?? [];
    final woundUncertain = result['wound_uncertain'] == true;
    final fusionWarning = result['fusion_warning']?.toString();
    final wEff = result['wound_effective_class']?.toString();
    final disc = result['disclaimer'];
    String discSummary = '';
    if (disc is Map && disc['summary'] != null) {
      discSummary = disc['summary'].toString();
    }

    final wd = result['wound_detail'];
    final ensembleKind = wd is Map ? wd['kind']?.toString() : null;

    if (!devMode) {
      return _SimpleResultColumn(
        cs: cs,
        retake: retake,
        severeBlur: severeBlur,
        iq: iq,
        woundUncertain: woundUncertain,
        wEff: wEff,
        fusionWarning: fusionWarning,
        displayTop: displayTop,
        predictionUncertain: predictionUncertain,
        conf: conf,
        snakes: snakes,
        discSummary: discSummary,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Fusion result',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.5),
        )
            .animate()
            .fadeIn(duration: 250.ms)
            .slideY(begin: 0.05, end: 0, duration: 300.ms, curve: Curves.easeOutCubic),
        const SizedBox(height: 6),
        Text(
          'Multimodal: wound CNN + symptoms + geography + context. This top pick can differ from the lab’s '
          '“Wound only” step, which uses the image branch alone.',
          style: TextStyle(fontSize: 13, height: 1.4, color: cs.onSurfaceVariant, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 14),
        if (!compact && wd is Map)
          _WoundBranchCard(
            woundDetail: Map<String, dynamic>.from(wd),
            ensembleKind: ensembleKind,
          ),
        const SizedBox(height: 12),
        // Only surface blur/retake when the backend says the photo is actually bad.
        if (retake)
          _Banner(
            icon: severeBlur ? Icons.add_a_photo_rounded : Icons.blur_on_rounded,
            color: severeBlur ? cs.errorContainer : cs.tertiaryContainer,
            onColor: severeBlur ? cs.error : cs.onTertiaryContainer,
            title: severeBlur ? 'Please reupload' : 'Photo quality',
            body: iq['message']?.toString() ?? 'Image may be unclear. Consider retaking.',
          ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.06, end: 0),
        if (woundUncertain)
          _Banner(
            icon: Icons.warning_amber_rounded,
            color: cs.errorContainer.withValues(alpha: 0.65),
            onColor: cs.onErrorContainer,
            title: 'Wound read uncertain',
            body:
                'Effective class: ${wEff ?? "unknown"}. Do not rely on wound class alone. Use clinical assessment.',
          ),
        if (fusionWarning != null && fusionWarning.isNotEmpty)
          _Banner(
            icon: Icons.cloud_off_rounded,
            color: cs.surfaceContainerHighest,
            onColor: cs.onSurfaceVariant,
            title: 'Image model not on server',
            body: fusionWarning,
          ),
        if (predictionUncertain)
          _Banner(
            icon: Icons.help_outline_rounded,
            color: cs.tertiaryContainer.withValues(alpha: 0.85),
            onColor: cs.onTertiaryContainer,
            title: 'Fused result not certain',
            body:
                'Best-guess class confidence is under 60%. Treat the venom pattern as unknown for triage purposes. See `display_top_class` in API.',
          ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [cs.primary.withValues(alpha: 0.12), cs.secondary.withValues(alpha: 0.08)],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.5)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'FUSED VENOM-TYPE (ALL INPUTS)',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.1,
                  color: cs.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                displayTop.toUpperCase(),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: cs.primary,
                      letterSpacing: 1.2,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                predictionUncertain
                    ? '${(100 * conf).toStringAsFixed(1)}% — below threshold, not a firm type'
                    : '${(100 * conf).toStringAsFixed(1)}% fused confidence',
                style: TextStyle(color: cs.onSurfaceVariant, fontWeight: FontWeight.w600, fontSize: 15),
              ),
            ],
          ),
        ).animate().fadeIn(delay: 100.ms).scale(begin: const Offset(0.98, 0.98), duration: 350.ms, curve: Curves.easeOutBack),
        const SizedBox(height: 22),
        Text('Venom-type distribution', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        ...List.generate(classes.length, (i) {
          final p = i < probs.length ? probs[i] : 0.0;
          return Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        classes[i],
                        style: const TextStyle(fontWeight: FontWeight.w600),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${(100 * p).toStringAsFixed(1)}%',
                      style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: TweenAnimationBuilder<double>(
                    tween: Tween(begin: 0, end: p.clamp(0.0, 1.0)),
                    duration: Duration(milliseconds: 600 + i * 80),
                    curve: Curves.easeOutCubic,
                    builder: (context, v, _) => LinearProgressIndicator(
                      value: v,
                      minHeight: 10,
                      backgroundColor: cs.surfaceContainerHighest,
                    ),
                  ),
                ),
              ],
            ),
          );
        }),
        if (ranked.isNotEmpty) ...[
          const SizedBox(height: 18),
          Text('Your symptoms (ranked)', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          ...ranked.take(12).map((x) {
            final m = x as Map;
            final lab = m['label']?.toString() ?? m['value']?.toString() ?? '';
            final sal = m['salience']?.toString() ?? '';
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.arrow_forward_ios_rounded, size: 12, color: cs.primary),
                  const SizedBox(width: 8),
                  Expanded(child: Text('$lab  ·  salience $sal', style: const TextStyle(fontSize: 13.5, height: 1.4))),
                ],
              ),
            );
          }),
        ],
        if (snakes.isNotEmpty) ...[
          const SizedBox(height: 18),
          Text('Likely snakes in region', style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          ...snakes.take(10).map((s) {
            final m = s as Map;
            final name = m['name']?.toString() ?? '';
            final sci = m['scientific_name']?.toString();
            final sc = m['score'];
            final scoreStr = sc != null ? (sc is num ? sc.toStringAsFixed(3) : sc.toString()) : '';
            return _SnakeRow(
              name: name,
              scientificName: sci,
              scoreLabel: scoreStr,
              cs: cs,
            );
          }),
        ],
        if (!compact) ...[
          const SizedBox(height: 12),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            title: const Text('Wound vs symptoms vs geo', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
            children: [
              ListTile(
                dense: true,
                title: Text(
                  'Wound effective: ${wEff ?? "?"}  ·  ensemble max '
                  '${result['wound_ensemble_max_confidence'] != null ? (100 * (result['wound_ensemble_max_confidence'] as num)).toStringAsFixed(1) : "?"}%',
                ),
              ),
              ListTile(
                dense: true,
                title: Text('Wound CNN: ${result['wound_only_top_class']} (${_pct(result['wound_only_confidence'])})'),
              ),
              ListTile(
                dense: true,
                title: Text('Symptom KB: ${result['symptom_only_top_class']} (${_pct(result['symptom_only_confidence'])})'),
              ),
              ListTile(
                dense: true,
                title: Text('Geo: ${result['geo_only_top_class']} (${_pct(result['geo_only_confidence'])})'),
              ),
            ],
          ),
        ],
        if (discSummary.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(discSummary, style: TextStyle(fontSize: 11.5, color: cs.onSurfaceVariant, height: 1.45)),
        ],
      ],
    );
  }

  static String _pct(dynamic v) {
    if (v == null) return '?';
    final n = (v as num).toDouble();
    return '${(100 * n).toStringAsFixed(1)}%';
  }
}

/// Minimal analysis: fused class, likely snakes, safety banners. No per-model rows.
class _SimpleResultColumn extends StatelessWidget {
  const _SimpleResultColumn({
    required this.cs,
    required this.retake,
    required this.severeBlur,
    required this.iq,
    required this.woundUncertain,
    required this.wEff,
    required this.fusionWarning,
    required this.displayTop,
    required this.predictionUncertain,
    required this.conf,
    required this.snakes,
    required this.discSummary,
  });

  final ColorScheme cs;
  final bool retake;
  final bool severeBlur;
  final dynamic iq;
  final bool woundUncertain;
  final String? wEff;
  final String? fusionWarning;
  final String displayTop;
  final bool predictionUncertain;
  final double conf;
  final List<dynamic> snakes;
  final String discSummary;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Result',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.5),
        )
            .animate()
            .fadeIn(duration: 250.ms)
            .slideY(begin: 0.05, end: 0, duration: 300.ms, curve: Curves.easeOutCubic),
        const SizedBox(height: 6),
        Text(
          'Fused assessment from your photo, symptoms, and location. Use the toolbar icon for full model breakdown.',
          style: TextStyle(fontSize: 13, height: 1.4, color: cs.onSurfaceVariant, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 14),
        if (retake)
          _Banner(
            icon: severeBlur ? Icons.add_a_photo_rounded : Icons.blur_on_rounded,
            color: severeBlur ? cs.errorContainer : cs.tertiaryContainer,
            onColor: severeBlur ? cs.error : cs.onTertiaryContainer,
            title: severeBlur ? 'Please reupload' : 'Photo quality',
            body: iq is Map ? (iq['message']?.toString() ?? 'Image may be unclear. Consider retaking.') : 'Image may be unclear. Consider retaking.',
          ).animate().fadeIn(duration: 350.ms).slideY(begin: 0.06, end: 0),
        if (woundUncertain)
          _Banner(
            icon: Icons.warning_amber_rounded,
            color: cs.errorContainer.withValues(alpha: 0.65),
            onColor: cs.onErrorContainer,
            title: 'Wound read uncertain',
            body:
                'Effective class: ${wEff ?? "unknown"}. Do not rely on wound class alone. Use clinical assessment.',
          ),
        if (fusionWarning != null && fusionWarning!.isNotEmpty)
          _Banner(
            icon: Icons.cloud_off_rounded,
            color: cs.surfaceContainerHighest,
            onColor: cs.onSurfaceVariant,
            title: 'Image model not on server',
            body: fusionWarning!,
          ),
        if (predictionUncertain)
          _Banner(
            icon: Icons.help_outline_rounded,
            color: cs.tertiaryContainer.withValues(alpha: 0.85),
            onColor: cs.onTertiaryContainer,
            title: 'Fused result not certain',
            body:
                'Best-guess class confidence is under 60%. Treat the venom pattern as unknown and use clinical assessment — do not rely on this screen alone.',
          ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [cs.primary.withValues(alpha: 0.12), cs.secondary.withValues(alpha: 0.08)],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.5)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'LIKELY VENOM PATTERN',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.1,
                  color: cs.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                displayTop.toUpperCase(),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: cs.primary,
                      letterSpacing: 1.2,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                predictionUncertain
                    ? '${(100 * conf).toStringAsFixed(1)}% — below threshold, not a firm type'
                    : '${(100 * conf).toStringAsFixed(1)}% confidence',
                style: TextStyle(color: cs.onSurfaceVariant, fontWeight: FontWeight.w600, fontSize: 15),
              ),
            ],
          ),
        ).animate().fadeIn(delay: 100.ms).scale(begin: const Offset(0.98, 0.98), duration: 350.ms, curve: Curves.easeOutBack),
        if (snakes.isNotEmpty) ...[
          const SizedBox(height: 22),
          Text(
            'Most likely snakes (regional)',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          ...snakes.take(8).map((s) {
            final m = s as Map;
            final name = m['name']?.toString() ?? '';
            final sci = m['scientific_name']?.toString();
            final sc = m['score'];
            final scoreStr = sc != null ? (sc is num ? sc.toStringAsFixed(3) : sc.toString()) : '';
            return _SnakeRow(
              name: name,
              scientificName: sci,
              scoreLabel: scoreStr,
              cs: cs,
            );
          }),
        ],
        if (discSummary.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text(discSummary, style: TextStyle(fontSize: 11.5, color: cs.onSurfaceVariant, height: 1.45)),
        ],
      ],
    );
  }
}

class _SnakeRow extends StatelessWidget {
  const _SnakeRow({
    required this.name,
    required this.scientificName,
    required this.scoreLabel,
    required this.cs,
  });

  final String name;
  final String? scientificName;
  final String scoreLabel;
  final ColorScheme cs;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.eco_rounded, color: cs.primary, size: 24),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
                if (scientificName != null && scientificName!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      scientificName!,
                      style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
            ),
          ),
          if (scoreLabel.isNotEmpty) ...[
            const SizedBox(width: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 72),
              child: Text(
                scoreLabel,
                style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant, fontWeight: FontWeight.w600),
                textAlign: TextAlign.right,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Shows per-backbone lines matching lab `/test/wound` (ensemble softmax fusion).
class _WoundBranchCard extends StatelessWidget {
  const _WoundBranchCard({required this.woundDetail, this.ensembleKind});

  final Map<String, dynamic> woundDetail;
  final String? ensembleKind;

  static const _order = ['efficientnet_b3', 'resnet50', 'densenet121'];

  static String _shortName(String k) {
    switch (k) {
      case 'efficientnet_b3':
        return 'EfficientNet-B3';
      case 'resnet50':
        return 'ResNet50';
      case 'densenet121':
        return 'DenseNet121';
      default:
        return k;
    }
  }

  String _weightCaption() {
    final w = woundDetail['ensemble_weights'];
    if (w is! List || w.isEmpty) {
      return 'EfficientNet-B3 58% · ResNet50 26% · DenseNet121 16% (defaults)';
    }
    final parts = <String>[];
    for (var i = 0; i < _order.length && i < w.length; i++) {
      final pct = (100 * (w[i] as num).toDouble()).toStringAsFixed(0);
      parts.add('${_shortName(_order[i])} $pct%');
    }
    return parts.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final modelsRaw = woundDetail['models'];

    if (ensembleKind == 'single') {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.45)),
        ),
        child: Text(
          'Wound branch: single-backbone checkpoint (not the 3-model ensemble). '
          'Train with `make train` and deploy `wound_ensemble.pt` to match the lab.',
          style: TextStyle(fontSize: 13, height: 1.4, color: cs.onSurfaceVariant),
        ),
      );
    }

    if (modelsRaw is! Map) {
      return const SizedBox.shrink();
    }

    final rows = <Widget>[
      Text(
        'Wound image branch (3-backbone ensemble)',
        style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 4),
      Text(
        'Softmax fusion: ${_weightCaption()}. Matches lab “Wound / fused ensemble”.',
        style: TextStyle(fontSize: 12.5, height: 1.35, color: cs.onSurfaceVariant),
      ),
      const SizedBox(height: 12),
    ];

    var backboneRows = 0;
    for (final name in _order) {
      final m = modelsRaw[name];
      if (m is! Map) continue;
      backboneRows++;
      final tc = m['top_class']?.toString() ?? '?';
      final tconf = m['top_confidence'];
      final pct = tconf is num ? (100 * tconf.toDouble()).toStringAsFixed(1) : '?';
      rows.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.layers_outlined, size: 18, color: AppTheme.neon),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${_shortName(name)} → $tc  ($pct%)',
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5, height: 1.25),
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (backboneRows == 0) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.neon.withValues(alpha: 0.35)),
        color: cs.surfaceContainerHighest.withValues(alpha: 0.35),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: rows),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({
    required this.icon,
    required this.color,
    required this.onColor,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final Color color;
  final Color onColor;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF161E2E),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.55)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: onColor, size: 26),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: AppTheme.ink,
                    fontWeight: FontWeight.w800,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: TextStyle(
                    color: AppTheme.ink.withValues(alpha: 0.92),
                    height: 1.4,
                    fontWeight: FontWeight.w500,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
