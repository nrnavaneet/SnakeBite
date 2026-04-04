import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

/// Client-side sharpness check aligned with [ml/image_quality.py] (Laplacian variance).
/// **Lenient:** only **extreme** blur blocks analysis; mild softness has no warning.
class LocalImageQualityResult {
  const LocalImageQualityResult({
    required this.sharpnessScore,
    required this.blocksProceed,
    required this.extremeBlur,
    this.message,
    this.errorReason,
  });

  final double? sharpnessScore;

  /// True only for unreadable files or extreme blur — user must pick another photo to analyze.
  final bool blocksProceed;

  /// Same idea as API `severe_blur` (extreme softness only).
  final bool extremeBlur;
  final String? message;
  final String? errorReason;

  static LocalImageQualityResult unreadable(String msg) => LocalImageQualityResult(
        sharpnessScore: null,
        blocksProceed: true,
        extremeBlur: true,
        message: msg,
        errorReason: 'unreadable',
      );
}

/// Must match `ml/image_quality._EXTREME_BLUR_MAX` — below this, photo is treated as unusable.
const double kExtremeBlurLaplacianMax = 32.0;

/// Decode [bytes] (JPEG/PNG), downscale like the server (max side 768), Laplacian variance.
Future<LocalImageQualityResult> assessImageQualityLocal(Uint8List bytes) async {
  ui.Codec? codec;
  try {
    codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final img = frame.image;
    try {
      final w = img.width;
      final h = img.height;
      if (w < 3 || h < 3) {
        return LocalImageQualityResult.unreadable('Image is too small — try another photo.');
      }
      final bd = await img.toByteData(format: ui.ImageByteFormat.rawRgba);
      if (bd == null) {
        return LocalImageQualityResult.unreadable('Could not read image pixels — try JPG or PNG.');
      }
      final rgba = bd.buffer.asUint8List();
      final maxD = math.max(w, h);
      final scale = maxD > 768 ? 768 / maxD : 1.0;
      final nw = math.max(3, (w * scale).round());
      final nh = math.max(3, (h * scale).round());
      final gray = Float64List(nw * nh);
      _fillGrayBilinear(rgba, w, h, gray, nw, nh, scale);
      final score = _laplacianVariance(gray, nw, nh);
      final extreme = score < kExtremeBlurLaplacianMax;
      String? msg;
      if (extreme) {
        msg =
            'This photo is extremely blurry — add a clearer picture to continue. '
            'Use bright light, hold steady, and tap the bite area to focus.';
      }
      return LocalImageQualityResult(
        sharpnessScore: double.parse(score.toStringAsFixed(2)),
        blocksProceed: extreme,
        extremeBlur: extreme,
        message: msg,
      );
    } finally {
      img.dispose();
    }
  } catch (_) {
    return LocalImageQualityResult.unreadable('Could not read the image — try a standard JPG or PNG.');
  } finally {
    codec?.dispose();
  }
}

void _fillGrayBilinear(
  Uint8List rgba,
  int w,
  int h,
  Float64List gray,
  int nw,
  int nh,
  double scale,
) {
  for (var y = 0; y < nh; y++) {
    final sy = (y + 0.5) / scale - 0.5;
    final y0 = sy.floor().clamp(0, h - 1);
    final y1 = (y0 + 1).clamp(0, h - 1);
    final fy = sy - y0;
    for (var x = 0; x < nw; x++) {
      final sx = (x + 0.5) / scale - 0.5;
      final x0 = sx.floor().clamp(0, w - 1);
      final x1 = (x0 + 1).clamp(0, w - 1);
      final fx = sx - x0;
      final g00 = _grayAt(rgba, w, x0, y0);
      final g10 = _grayAt(rgba, w, x1, y0);
      final g01 = _grayAt(rgba, w, x0, y1);
      final g11 = _grayAt(rgba, w, x1, y1);
      final g0 = g00 * (1 - fx) + g10 * fx;
      final g1 = g01 * (1 - fx) + g11 * fx;
      gray[y * nw + x] = g0 * (1 - fy) + g1 * fy;
    }
  }
}

double _grayAt(Uint8List rgba, int w, int x, int y) {
  final i = (y * w + x) * 4;
  final r = rgba[i].toDouble();
  final g = rgba[i + 1].toDouble();
  final b = rgba[i + 2].toDouble();
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

/// Variance of discrete Laplacian (interior pixels), matching numpy `lap.var()`.
double _laplacianVariance(Float64List g, int w, int h) {
  if (w < 3 || h < 3) return 0;
  var sum = 0.0;
  var sumSq = 0.0;
  var n = 0;
  for (var y = 1; y < h - 1; y++) {
    for (var x = 1; x < w - 1; x++) {
      final v = g[(y - 1) * w + x] +
          g[(y + 1) * w + x] +
          g[y * w + x - 1] +
          g[y * w + x + 1] -
          4.0 * g[y * w + x];
      sum += v;
      sumSq += v * v;
      n++;
    }
  }
  if (n == 0) return 0;
  final mean = sum / n;
  return sumSq / n - mean * mean;
}
