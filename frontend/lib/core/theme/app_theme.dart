import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

/// Heading style (Manrope, bold) used by titles, numbers and the logo.
class AppStyle extends ThemeExtension<AppStyle> {
  const AppStyle({required this.heading});

  final TextStyle heading;

  @override
  AppStyle copyWith({TextStyle? heading}) => AppStyle(heading: heading ?? this.heading);

  @override
  AppStyle lerp(ThemeExtension<AppStyle>? other, double t) {
    if (other is! AppStyle) return this;
    return AppStyle(heading: TextStyle.lerp(heading, other.heading, t)!);
  }
}

extension AppStyleContext on BuildContext {
  /// Heading text style at [size] (CSS px of the design).
  TextStyle heading(
    double size, {
    Color color = AppColors.ink,
    FontWeight weight = FontWeight.w800,
    double? height,
    double? letterSpacing,
  }) {
    final base = Theme.of(this).extension<AppStyle>()!.heading;
    return base.copyWith(
      fontSize: size,
      color: color,
      fontWeight: weight,
      height: height,
      letterSpacing: letterSpacing,
    );
  }
}

class AppTheme {
  const AppTheme._();

  /// [webFonts] loads DM Sans and Manrope from Google Fonts, like the design does. Tests turn
  /// it off so they never touch the network.
  static ThemeData build({bool webFonts = true}) {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.teal,
      primary: AppColors.primary,
      surface: AppColors.white,
      error: AppColors.error,
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.background,
      splashFactory: InkRipple.splashFactory,
    );
    final text = webFonts
        ? GoogleFonts.dmSansTextTheme(base.textTheme).apply(bodyColor: AppColors.ink, displayColor: AppColors.ink)
        : base.textTheme.apply(bodyColor: AppColors.ink, displayColor: AppColors.ink);
    final heading = webFonts
        ? GoogleFonts.manrope(fontWeight: FontWeight.w800)
        : const TextStyle(fontWeight: FontWeight.w800);

    OutlineInputBorder border(Color color, [double width = 1]) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: BorderSide(color: color, width: width),
    );

    return base.copyWith(
      textTheme: text,
      extensions: [AppStyle(heading: heading)],
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.white,
        isDense: false,
        contentPadding: const EdgeInsets.symmetric(horizontal: 13, vertical: 14),
        hintStyle: const TextStyle(color: AppColors.textFaint, fontSize: 13),
        border: border(AppColors.fieldBorder),
        enabledBorder: border(AppColors.fieldBorder),
        focusedBorder: border(AppColors.focus, 2),
        errorBorder: border(AppColors.error),
        focusedErrorBorder: border(AppColors.error, 2),
        disabledBorder: border(AppColors.fieldBorder),
        errorStyle: const TextStyle(color: AppColors.error, fontSize: 11),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.toast,
        contentTextStyle: text.bodyMedium?.copyWith(color: Colors.white, fontSize: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(color: AppColors.toast, borderRadius: BorderRadius.circular(6)),
        textStyle: const TextStyle(color: Colors.white, fontSize: 11),
      ),
    );
  }
}
