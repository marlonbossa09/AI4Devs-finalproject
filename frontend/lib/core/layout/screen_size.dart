import 'package:flutter/widgets.dart';

/// Breakpoints of the design: up to 700 px is mobile, up to 1100 px is tablet.
enum ScreenSize {
  mobile,
  tablet,
  desktop;

  static ScreenSize of(double width) {
    if (width <= 700) return ScreenSize.mobile;
    if (width <= 1100) return ScreenSize.tablet;
    return ScreenSize.desktop;
  }

  static ScreenSize ofContext(BuildContext context) => of(MediaQuery.sizeOf(context).width);

  bool get isMobile => this == ScreenSize.mobile;
  bool get isDesktop => this == ScreenSize.desktop;
}
