import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Immersive dark “clinical HUD” — neon teal, depth, glass. Tuned for OLED + web.
class AppTheme {
  AppTheme._();

  static const Color neon = Color(0xFF2DD4BF);
  static const Color neonDim = Color(0xFF14B8A6);
  /// Aliases for older call sites (same as neon stack).
  static const Color primary = neon;
  static const Color primaryDark = neonDim;
  static const Color violet = Color(0xFFA78BFA);
  static const Color rose = Color(0xFFFB7185);
  static const Color void_ = Color(0xFF05080D);
  static const Color surface = Color(0xFF0C1118);
  static const Color surfaceElevated = Color(0xFF141B26);
  /// Opaque bars so scrolling content does not show through app / drawer headers.
  static const Color shellAppBarBackground = Color(0xFF080C12);
  static const Color shellNavBarBackground = Color(0xFF141B26);
  static const Color glass = Color(0x1AFFFFFF);
  static const Color ink = Color(0xFFE8EEF5);
  static const Color inkMuted = Color(0xFF94A3B8);

  /// Deep space + bioluminescence mesh.
  static LinearGradient get scaffoldGradient => const LinearGradient(
        begin: Alignment(-1.2, -0.9),
        end: Alignment(1.3, 1.4),
        colors: [
          Color(0xFF020617),
          Color(0xFF0C1220),
          Color(0xFF134E4A),
          Color(0xFF1E1B4B),
          Color(0xFF0F172A),
        ],
        stops: [0.0, 0.28, 0.52, 0.72, 1.0],
      );

  static LinearGradient get heroButtonGradient => const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF5EEAD4), neonDim, Color(0xFF0D9488)],
      );

  static ThemeData dark() {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme(
        brightness: Brightness.dark,
        primary: neon,
        onPrimary: void_,
        primaryContainer: neonDim.withValues(alpha: 0.35),
        onPrimaryContainer: ink,
        secondary: violet,
        onSecondary: void_,
        tertiary: rose,
        onTertiary: void_,
        error: const Color(0xFFF87171),
        onError: void_,
        surface: surface,
        onSurface: ink,
        onSurfaceVariant: inkMuted,
        outline: Colors.white24,
        outlineVariant: Colors.white12,
        shadow: Colors.black,
        surfaceContainerHighest: surfaceElevated,
        surfaceContainerHigh: const Color(0xFF1E293B),
        surfaceContainer: const Color(0xFF1A2332),
      ),
    );

    final text = GoogleFonts.dmSansTextTheme(base.textTheme).apply(
      bodyColor: ink,
      displayColor: ink,
    );

    return base.copyWith(
      scaffoldBackgroundColor: Colors.transparent,
      textTheme: text.copyWith(
        headlineLarge: GoogleFonts.outfit(
          textStyle: text.headlineLarge,
          fontWeight: FontWeight.w700,
          letterSpacing: -1.2,
        ),
        headlineMedium: GoogleFonts.outfit(
          textStyle: text.headlineMedium,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.8,
        ),
        titleLarge: GoogleFonts.outfit(
          textStyle: text.titleLarge,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
      ),
      appBarTheme: AppBarTheme(
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: shellAppBarBackground,
        foregroundColor: ink,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: GoogleFonts.outfit(
          fontSize: 19,
          fontWeight: FontWeight.w700,
          color: ink,
          letterSpacing: -0.4,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: surfaceElevated.withValues(alpha: 0.55),
        surfaceTintColor: Colors.transparent,
        shadowColor: neon.withValues(alpha: 0.08),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 64,
        elevation: 0,
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        indicatorColor: neon.withValues(alpha: 0.22),
        iconTheme: WidgetStateProperty.resolveWith((s) {
          final sel = s.contains(WidgetState.selected);
          return IconThemeData(
            size: 26,
            color: sel ? neon : inkMuted,
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((s) {
          final w = s.contains(WidgetState.selected) ? FontWeight.w800 : FontWeight.w600;
          return GoogleFonts.dmSans(
            fontSize: 11,
            fontWeight: w,
            letterSpacing: 0.4,
            color: s.contains(WidgetState.selected) ? neon : inkMuted,
          );
        }),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceElevated.withValues(alpha: 0.8),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.12)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: neon.withValues(alpha: 0.65), width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        labelStyle: TextStyle(color: inkMuted),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 28),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ink,
          side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: neon,
        thumbColor: neon,
        overlayColor: neon.withValues(alpha: 0.2),
        inactiveTrackColor: Colors.white.withValues(alpha: 0.12),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surfaceElevated,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      ),
    );
  }
}
