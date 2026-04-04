import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Deeper clinical aesthetic: slate + teal, soft gradients, premium cards.
class AppTheme {
  AppTheme._();

  static const Color primary = Color(0xFF0D9488);
  static const Color primaryDark = Color(0xFF0F766E);
  static const Color surface = Color(0xFFF8FAFC);
  static const Color surfaceDeep = Color(0xFFF1F5F9);
  static const Color surfaceCard = Color(0xFFFFFFFF);
  static const Color ink = Color(0xFF0F172A);
  static const Color accentAmber = Color(0xFFF59E0B);

  static LinearGradient get scaffoldGradient => const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Color(0xFFE0F2FE),
          Color(0xFFF8FAFC),
          Color(0xFFECFDF5),
        ],
        stops: [0.0, 0.45, 1.0],
      );

  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        brightness: Brightness.light,
        surface: surfaceDeep,
        primary: primaryDark,
        onPrimary: Colors.white,
        secondary: const Color(0xFF14B8A6),
        tertiary: accentAmber,
        surfaceContainerHighest: const Color(0xFFE2E8F0),
      ),
    );
    final text = GoogleFonts.plusJakartaSansTextTheme(base.textTheme).apply(
      bodyColor: ink,
      displayColor: ink,
    );
    return base.copyWith(
      scaffoldBackgroundColor: Colors.transparent,
      textTheme: text,
      appBarTheme: AppBarTheme(
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: ink,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: ink,
          letterSpacing: -0.6,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: surfaceCard,
        surfaceTintColor: Colors.transparent,
        shadowColor: const Color(0xFF0F172A).withValues(alpha: 0.08),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(color: base.colorScheme.outlineVariant.withValues(alpha: 0.25)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 72,
        elevation: 0,
        shadowColor: Colors.transparent,
        backgroundColor: surfaceCard.withValues(alpha: 0.92),
        surfaceTintColor: Colors.transparent,
        indicatorColor: primary.withValues(alpha: 0.18),
        labelTextStyle: WidgetStateProperty.resolveWith((s) {
          final w = s.contains(WidgetState.selected) ? FontWeight.w800 : FontWeight.w600;
          return GoogleFonts.plusJakartaSans(fontSize: 12, fontWeight: w, letterSpacing: 0.2);
        }),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceCard,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 28),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          elevation: 0,
          shadowColor: primaryDark.withValues(alpha: 0.45),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: primaryDark,
        thumbColor: primaryDark,
        overlayColor: primary.withValues(alpha: 0.15),
        inactiveTrackColor: base.colorScheme.surfaceContainerHighest,
      ),
    );
  }
}
