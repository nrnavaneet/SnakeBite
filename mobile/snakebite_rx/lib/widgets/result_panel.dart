import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

class ResultPanel extends StatelessWidget {
  const ResultPanel({super.key, required this.result, this.compact = false});

  final Map<String, dynamic> result;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final iq = result['image_quality'];
    final retake = iq is Map && iq['recommend_retake'] == true;
    final top = result['top_class']?.toString() ?? '';
    final conf = (result['top_confidence'] as num?)?.toDouble() ?? 0;
    final classes = (result['classes'] as List?)?.map((e) => e.toString()).toList() ?? [];
    final probs = (result['final_probability'] as List?)?.map((e) => (e as num).toDouble()).toList() ?? [];
    final snakes = (result['snake_species_top'] as List?) ?? [];
    final ranked = (result['selected_symptoms_ranked'] as List?) ?? [];
    final woundUncertain = result['wound_uncertain'] == true;
    final wEff = result['wound_effective_class']?.toString();
    final disc = result['disclaimer'];
    String discSummary = '';
    if (disc is Map && disc['summary'] != null) {
      discSummary = disc['summary'].toString();
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
        const SizedBox(height: 8),
        // Only surface blur/retake when the backend says the photo is actually bad.
        if (retake)
          _Banner(
            icon: Icons.blur_on_rounded,
            color: cs.tertiaryContainer,
            onColor: cs.onTertiaryContainer,
            title: 'Photo quality',
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
                top.toUpperCase(),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: cs.primary,
                      letterSpacing: 1.2,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                '${(100 * conf).toStringAsFixed(1)}% fused confidence',
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
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(classes[i], style: const TextStyle(fontWeight: FontWeight.w600)),
                    Text('${(100 * p).toStringAsFixed(1)}%', style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13)),
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
            return ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.eco_rounded, color: cs.primary, size: 24),
              title: Text(name, style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: sci != null && sci.isNotEmpty ? Text(sci, style: const TextStyle(fontSize: 12)) : null,
              trailing: Text(
                sc != null ? (sc is num ? sc.toStringAsFixed(3) : sc.toString()) : '',
                style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
              ),
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
        color: color,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant.withValues(alpha: 0.4)),
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
                Text(title, style: TextStyle(color: onColor, fontWeight: FontWeight.w800, fontSize: 13)),
                const SizedBox(height: 4),
                Text(body, style: TextStyle(color: onColor.withValues(alpha: 0.95), height: 1.35, fontWeight: FontWeight.w500)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
