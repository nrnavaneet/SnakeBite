import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/app_theme.dart';

/// Full transparency view: same numbers as lab.html atomic steps, from one `/predict` response.
class LabParityBreakdown extends StatelessWidget {
  const LabParityBreakdown({super.key, required this.result});

  final Map<String, dynamic> result;

  static List<String> _classes(Map<String, dynamic> result) {
    final c = result['classes'];
    if (c is! List) return [];
    return c.map((e) => e.toString()).toList();
  }

  static List<double>? _probList(dynamic x) {
    if (x is! List || x.isEmpty) return null;
    try {
      return x.map((e) => (e as num).toDouble()).toList();
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final classes = _classes(result);
    final debug = result['debug'];
    final fusionExpl = result['fusion_explanation'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.science_outlined, size: 22, color: AppTheme.neon),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Atomic breakdown (testing)',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.4,
                    ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          'Parsed from this /predict response — compare with lab.html steps (wound → geo → symptoms → full).',
          style: TextStyle(fontSize: 12.5, height: 1.4, color: cs.onSurfaceVariant),
        ),
        const SizedBox(height: 16),
        if (debug is Map) _ModalityWeightsCard(debug: Map<String, dynamic>.from(debug), cs: cs),
        if (fusionExpl is Map) ...[
          const SizedBox(height: 12),
          _FusionExplCard(fusionExpl: Map<String, dynamic>.from(fusionExpl), cs: cs),
        ],
        const SizedBox(height: 12),
        _DistributionSection(
          title: 'Wound branch — fused (matches lab /test/wound)',
          subtitle: 'Weighted softmax of the three CNNs; vector is wound_probability in JSON.',
          classes: classes,
          probs: _probList(result['wound_probability']),
          cs: cs,
          accent: AppTheme.neon,
        ),
        const SizedBox(height: 8),
        _PerBackboneSection(result: result, classes: classes, cs: cs),
        const SizedBox(height: 12),
        _DistributionSection(
          title: 'Symptom KB only (matches lab /test/symptoms)',
          subtitle: 'symptom_probability — raw from API',
          classes: classes,
          probs: _probList(result['symptom_probability']),
          cs: cs,
          accent: AppTheme.violet,
        ),
        if (debug is Map && _probList(debug['symptom_probability_adjusted']) != null) ...[
          const SizedBox(height: 12),
          _DistributionSection(
            title: 'Symptom KB — used inside /predict fusion',
            subtitle: 'debug.symptom_probability_adjusted (per-class floor so one-hot KB cannot veto wound)',
            classes: classes,
            probs: _probList(debug['symptom_probability_adjusted']),
            cs: cs,
            accent: AppTheme.violet,
          ),
        ],
        const SizedBox(height: 12),
        _DistributionSection(
          title: 'Geo only (matches lab /test/geo)',
          subtitle: 'geo_probability — raw from API',
          classes: classes,
          probs: _probList(result['geo_probability']),
          cs: cs,
          accent: AppTheme.rose,
        ),
        if (debug is Map && _probList(debug['geo_probability_adjusted']) != null) ...[
          const SizedBox(height: 12),
          _DistributionSection(
            title: 'Geo — used inside /predict fusion',
            subtitle: 'debug.geo_probability_adjusted',
            classes: classes,
            probs: _probList(debug['geo_probability_adjusted']),
            cs: cs,
            accent: AppTheme.rose,
          ),
        ],
        if (debug is Map && debug['context_prior'] != null) ...[
          const SizedBox(height: 12),
          _DistributionSection(
            title: 'Context prior (time / circumstance / age / weight)',
            subtitle: 'debug.context_prior',
            classes: classes,
            probs: _probList(debug['context_prior']),
            cs: cs,
            accent: cs.secondary,
          ),
        ],
        const SizedBox(height: 12),
        _DistributionSection(
          title: 'Final multimodal (matches lab full /predict)',
          subtitle: 'final_probability — log blend using modality weights above',
          classes: classes,
          probs: _probList(result['final_probability']),
          cs: cs,
          accent: cs.primary,
        ),
        const SizedBox(height: 12),
        _RawJsonTile(result: result, cs: cs),
      ],
    );
  }
}

class _ModalityWeightsCard extends StatelessWidget {
  const _ModalityWeightsCard({required this.debug, required this.cs});

  final Map<String, dynamic> debug;
  final ColorScheme cs;

  @override
  Widget build(BuildContext context) {
    final mw = debug['modality_weights'];
    if (mw is! Map) {
      return Text('No debug.modality_weights in response.', style: TextStyle(color: cs.onSurfaceVariant));
    }
    final w = Map<String, dynamic>.from(mw);
    final lines = <String>[
      'wound: ${_pct(w['wound'])}',
      'symptom: ${_pct(w['symptom'])}',
      'geo: ${_pct(w['geo'])}',
      'context: ${_pct(w['context'])}',
    ];
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.neon.withValues(alpha: 0.35)),
        color: cs.surfaceContainerHighest.withValues(alpha: 0.4),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Fusion weights (this run)', style: TextStyle(fontWeight: FontWeight.w800, color: cs.onSurface)),
          const SizedBox(height: 8),
          ...lines.map((s) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(s, style: TextStyle(fontFamily: 'monospace', fontSize: 13, color: cs.onSurfaceVariant)),
              )),
        ],
      ),
    );
  }

  static String _pct(dynamic v) {
    if (v == null) return '?';
    return (100 * (v as num).toDouble()).toStringAsFixed(1) + '%';
  }
}

class _FusionExplCard extends StatelessWidget {
  const _FusionExplCard({required this.fusionExpl, required this.cs});

  final Map<String, dynamic> fusionExpl;
  final ColorScheme cs;

  @override
  Widget build(BuildContext context) {
    final wb = fusionExpl['wound_branch']?.toString() ?? '';
    final fm = fusionExpl['final_multimodal']?.toString() ?? '';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Server explanations', style: TextStyle(fontWeight: FontWeight.w800, color: cs.onSurface)),
          const SizedBox(height: 8),
          Text(wb, style: TextStyle(fontSize: 12.5, height: 1.45, color: cs.onSurfaceVariant)),
          const SizedBox(height: 10),
          Text(fm, style: TextStyle(fontSize: 12.5, height: 1.45, color: cs.onSurfaceVariant)),
        ],
      ),
    );
  }
}

class _DistributionSection extends StatelessWidget {
  const _DistributionSection({
    required this.title,
    required this.subtitle,
    required this.classes,
    required this.probs,
    required this.cs,
    required this.accent,
  });

  final String title;
  final String subtitle;
  final List<String> classes;
  final List<double>? probs;
  final ColorScheme cs;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    if (classes.isEmpty || probs == null || probs!.length != classes.length) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.4)),
        ),
        child: Text('$title — no vector in response', style: TextStyle(color: cs.onSurfaceVariant, fontSize: 13)),
      );
    }
    final p = probs!;
    final topI = _argMax(p);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
        color: cs.surfaceContainerHighest.withValues(alpha: 0.25),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: cs.onSurface)),
          const SizedBox(height: 4),
          Text(subtitle, style: TextStyle(fontSize: 11.5, color: cs.onSurfaceVariant)),
          const SizedBox(height: 6),
          Text(
            'argmax → ${classes[topI]} (${(100 * p[topI]).toStringAsFixed(1)}%)',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: accent),
          ),
          const SizedBox(height: 10),
          ...List.generate(classes.length, (i) {
            final v = i < p.length ? p[i].clamp(0.0, 1.0) : 0.0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: Text(
                      classes[i],
                      style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    flex: 3,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: v,
                        minHeight: 8,
                        backgroundColor: cs.surfaceContainerHighest,
                        color: accent.withValues(alpha: 0.65),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  SizedBox(
                    width: 40,
                    child: Text(
                      '${(100 * v).toStringAsFixed(1)}%',
                      style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
                      textAlign: TextAlign.right,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  static int _argMax(List<double> p) {
    var ix = 0;
    for (var i = 1; i < p.length; i++) {
      if (p[i] > p[ix]) ix = i;
    }
    return ix;
  }
}

class _PerBackboneSection extends StatelessWidget {
  const _PerBackboneSection({required this.result, required this.classes, required this.cs});

  final Map<String, dynamic> result;
  final List<String> classes;
  final ColorScheme cs;

  @override
  Widget build(BuildContext context) {
    final wd = result['wound_detail'];
    if (wd is! Map) {
      return Text('No wound_detail — wound model may be unloaded.', style: TextStyle(color: cs.onSurfaceVariant));
    }
    final kind = wd['kind']?.toString();
    if (kind != 'ensemble') {
      return Text('Single-backbone checkpoint — no per-model rows.', style: TextStyle(color: cs.onSurfaceVariant));
    }
    final models = wd['models'];
    if (models is! Map) return const SizedBox.shrink();

    const order = ['efficientnet_b3', 'resnet50', 'densenet121'];
    final children = <Widget>[
      Text(
        'Per-backbone (matches lab /test/wound/backbone)',
        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: cs.onSurface)),
      const SizedBox(height: 8),
    ];

    for (final name in order) {
      final m = models[name];
      if (m is! Map) continue;
      final top = m['top_class']?.toString() ?? '?';
      final tc = m['top_confidence'];
      final tcS = tc is num ? (100 * tc.toDouble()).toStringAsFixed(1) : '?';
      final rawProbs = LabParityBreakdown._probList(m['probability']);
      children.add(
        Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: cs.outlineVariant.withValues(alpha: 0.45)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_prettyName(name), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
              const SizedBox(height: 4),
              Text('top: $top  ·  confidence $tcS%', style: TextStyle(color: cs.onSurfaceVariant, fontSize: 12.5)),
              if (rawProbs != null && rawProbs.length == classes.length) ...[
                const SizedBox(height: 8),
                ...List.generate(classes.length, (i) {
                  final v = i < rawProbs.length ? rawProbs[i].clamp(0.0, 1.0) : 0.0;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      children: [
                        Expanded(
                          flex: 2,
                          child: Text(
                            classes[i],
                            style: const TextStyle(fontSize: 11.5),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Expanded(
                          flex: 3,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: v,
                              minHeight: 6,
                              backgroundColor: cs.surfaceContainerHighest,
                            ),
                          ),
                        ),
                        const SizedBox(width: 4),
                        SizedBox(
                          width: 38,
                          child: Text(
                            '${(100 * v).toStringAsFixed(1)}%',
                            style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant),
                            textAlign: TextAlign.right,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ],
          ),
        ),
      );
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: children);
  }

  static String _prettyName(String k) {
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
}

class _RawJsonTile extends StatefulWidget {
  const _RawJsonTile({required this.result, required this.cs});

  final Map<String, dynamic> result;
  final ColorScheme cs;

  @override
  State<_RawJsonTile> createState() => _RawJsonTileState();
}

class _RawJsonTileState extends State<_RawJsonTile> {
  @override
  Widget build(BuildContext context) {
    // Trim huge fields for copy: still include keys user needs
    final trimmed = <String, dynamic>{
      'classes': widget.result['classes'],
      'top_class': widget.result['top_class'],
      'display_top_class': widget.result['display_top_class'],
      'prediction_uncertain': widget.result['prediction_uncertain'],
      'top_confidence': widget.result['top_confidence'],
      'final_probability': widget.result['final_probability'],
      'wound_probability': widget.result['wound_probability'],
      'symptom_probability': widget.result['symptom_probability'],
      'geo_probability': widget.result['geo_probability'],
      'wound_detail': widget.result['wound_detail'],
      'debug': widget.result['debug'],
      'wound_model_loaded': widget.result['wound_model_loaded'],
      'wound_uncertain': widget.result['wound_uncertain'],
    };
    final json = const JsonEncoder.withIndent('  ').convert(trimmed);
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      title: Text('Raw JSON (subset)', style: TextStyle(fontWeight: FontWeight.w700, color: widget.cs.onSurface)),
      initiallyExpanded: false,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: json));
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied JSON')));
              }
            },
            icon: const Icon(Icons.copy, size: 18),
            label: const Text('Copy'),
          ),
        ),
        SelectableText(json, style: TextStyle(fontFamily: 'monospace', fontSize: 10.5, color: widget.cs.onSurfaceVariant, height: 1.35)),
      ],
    );
  }
}
