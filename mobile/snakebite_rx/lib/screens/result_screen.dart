import 'dart:typed_data';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../widgets/result_panel.dart';

/// Full-screen results with optional hero image. Blur overlay only when API flags bad quality.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result, this.imageBytes});

  final Map<String, dynamic> result;
  final Uint8List? imageBytes;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final iq = result['image_quality'];
    final badPhoto = iq is Map && iq['recommend_retake'] == true;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar.large(
            pinned: true,
            title: const Text('Analysis'),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back_rounded),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),
          if (imageBytes != null)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: AspectRatio(
                    aspectRatio: 4 / 3,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        Hero(
                          tag: 'wound_photo',
                          child: badPhoto
                              ? ImageFiltered(
                                  imageFilter: ImageFilter.blur(sigmaX: 9, sigmaY: 9),
                                  child: Image.memory(imageBytes!, fit: BoxFit.cover),
                                )
                              : Image.memory(imageBytes!, fit: BoxFit.cover),
                        ),
                        if (badPhoto)
                          Container(
                            color: Colors.black.withValues(alpha: 0.35),
                            alignment: Alignment.center,
                            child: Container(
                              margin: const EdgeInsets.all(24),
                              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                              decoration: BoxDecoration(
                                color: cs.surface.withValues(alpha: 0.92),
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.photo_camera_rounded, color: cs.primary),
                                  const SizedBox(width: 10),
                                  Flexible(
                                    child: Text(
                                      'Blur preview. Retake for a sharper photo',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w700,
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
                ).animate().fadeIn(duration: 400.ms).scale(begin: const Offset(0.97, 0.97), curve: Curves.easeOutCubic),
              ),
            ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 40),
            sliver: SliverToBoxAdapter(
              child: ResultPanel(result: result),
            ),
          ),
        ],
      ),
    );
  }
}
