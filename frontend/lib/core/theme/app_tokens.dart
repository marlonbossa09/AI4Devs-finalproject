import 'package:flutter/material.dart';

import '../layout/screen_size.dart';

/// Spacing scale (px): 4, 8, 12, 16, 20 and 24. Use these instead of loose numbers.
class AppSpace {
  const AppSpace._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
}

/// Corner radii: controls 8, cards 12, panels 16 (a pill is `pill`).
class AppRadius {
  const AppRadius._();

  static const double control = 8;
  static const double card = 12;
  static const double panel = 16;
  static const double pill = 999;
}

/// Type scale (px). Nothing informative goes below [caption] (12).
class AppType {
  const AppType._();

  /// Metadata, captions, hints, tags and pills.
  static const double caption = 12;

  /// Compact content (fields, buttons, lists).
  static const double body = 13;

  /// Content that needs a little more weight.
  static const double bodyLarge = 14;

  /// Title of a card or a panel.
  static const double cardTitle = 16;

  /// Title of a page.
  static const double pageTitle = 20;

  /// Highlighted figure of an indicator.
  static const double metric = 24;
}

/// Sizes of controls and touch targets.
class AppSize {
  const AppSize._();

  /// Height of a button or a field on a desktop or tablet.
  static const double controlDesktop = 40;

  /// Height of a button on a phone (bigger touch target).
  static const double controlMobile = 44;

  /// Smallest touch target of any interactive element.
  static const double minTouch = 40;

  /// Width of the focus ring drawn around a focused control.
  static const double focusRingWidth = 2;

  static double control(BuildContext context) =>
      ScreenSize.ofContext(context).isMobile ? controlMobile : controlDesktop;
}

/// Shadows. One soft shadow for a card; a lighter one for a raised control.
class AppShadow {
  const AppShadow._();

  static const card = [BoxShadow(color: Color(0x0A1A3450), blurRadius: 12, offset: Offset(0, 3))];
  static const primaryButton = [BoxShadow(color: Color(0x1F0E7C75), blurRadius: 10, offset: Offset(0, 4))];
}
