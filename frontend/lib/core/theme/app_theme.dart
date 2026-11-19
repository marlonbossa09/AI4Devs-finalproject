import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';
import 'app_tokens.dart';

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

  /// Type scale of the app (UX-T1), applied to the Material [TextTheme] so that any text without an explicit size follows it.
  /// 12 px metadata, 13 compact content, 14 emphasis, 16 card title, 20 page title and 24 highlighted figure.
  static TextTheme _scaled(TextTheme t) => t.copyWith(
    labelSmall: t.labelSmall?.copyWith(fontSize: AppType.caption),
    labelMedium: t.labelMedium?.copyWith(fontSize: AppType.caption),
    labelLarge: t.labelLarge?.copyWith(fontSize: AppType.body),
    bodySmall: t.bodySmall?.copyWith(fontSize: AppType.caption),
    bodyMedium: t.bodyMedium?.copyWith(fontSize: AppType.body),
    bodyLarge: t.bodyLarge?.copyWith(fontSize: AppType.bodyLarge),
    titleSmall: t.titleSmall?.copyWith(fontSize: AppType.bodyLarge),
    titleMedium: t.titleMedium?.copyWith(fontSize: AppType.cardTitle),
    titleLarge: t.titleLarge?.copyWith(fontSize: AppType.pageTitle),
    headlineSmall: t.headlineSmall?.copyWith(fontSize: AppType.metric),
  );

  /// [webFonts] loads DM Sans and Manrope from Google Fonts, like the design does. Tests turn
  /// it off so they never touch the network.
  static ThemeData build({bool webFonts = true}) {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.teal,
      primary: AppColors.primary,
      onPrimary: AppColors.white,
      surface: AppColors.surface,
      error: AppColors.error,
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.background,
      splashFactory: InkRipple.splashFactory,
      focusColor: AppColors.focusRing.withValues(alpha: 0.16),
      hoverColor: AppColors.hoverSurface,
    );
    final text = _scaled(
      webFonts
          ? GoogleFonts.dmSansTextTheme(base.textTheme).apply(bodyColor: AppColors.ink, displayColor: AppColors.ink)
          : base.textTheme.apply(bodyColor: AppColors.ink, displayColor: AppColors.ink),
    );
    final heading = webFonts
        ? GoogleFonts.manrope(fontWeight: FontWeight.w800)
        : const TextStyle(fontWeight: FontWeight.w800);

    OutlineInputBorder border(Color color, [double width = 1]) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadius.control),
      borderSide: BorderSide(color: color, width: width),
    );

    return base.copyWith(
      textTheme: text,
      extensions: [AppStyle(heading: heading)],
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.white,
        // Dense so that a one-line field is 40 px tall (the Material minimum for a non-dense field is 48).
        isDense: true,
        // The real font is shorter than the test font, so the height is also guaranteed here (a one-line field is 40 px).
        constraints: const BoxConstraints(minHeight: AppSize.controlDesktop),
        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: 10),
        hintStyle: const TextStyle(color: AppColors.textFaint, fontSize: AppType.body),
        border: border(AppColors.fieldBorder),
        enabledBorder: border(AppColors.fieldBorder),
        focusedBorder: border(AppColors.focusRing, AppSize.focusRingWidth),
        errorBorder: border(AppColors.error),
        focusedErrorBorder: border(AppColors.error, AppSize.focusRingWidth),
        disabledBorder: border(AppColors.fieldBorder),
        errorStyle: const TextStyle(color: AppColors.error, fontSize: AppType.caption),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.toast,
        contentTextStyle: text.bodyMedium?.copyWith(color: Colors.white, fontSize: AppType.caption),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.control)),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(color: AppColors.toast, borderRadius: BorderRadius.circular(6)),
        textStyle: const TextStyle(color: Colors.white, fontSize: AppType.caption),
      ),
    );
  }
}
