import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_tokens.dart';

/// An [InkWell] that draws a visible 2 px focus ring (`AppColors.focusRing`) around itself when it is reached with the
/// keyboard. The ink effects of Material are too faint to be a focus indicator on their own.
class FocusRingInk extends StatefulWidget {
  const FocusRingInk({
    super.key,
    required this.child,
    required this.onTap,
    this.borderRadius = const BorderRadius.all(Radius.circular(AppRadius.control)),
    this.shape,
    this.inkKey,
  });

  final Widget child;
  final VoidCallback? onTap;
  final BorderRadius borderRadius;

  /// When set (a circle), the ring and the ink use this shape instead of [borderRadius].
  final ShapeBorder? shape;

  /// Key of the inner [InkWell], so tests and automation can find it.
  final Key? inkKey;

  @override
  State<FocusRingInk> createState() => _FocusRingInkState();
}

class _FocusRingInkState extends State<FocusRingInk> {
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final circle = widget.shape is CircleBorder;
    return DecoratedBox(
      position: DecorationPosition.foreground,
      decoration: BoxDecoration(
        shape: circle ? BoxShape.circle : BoxShape.rectangle,
        borderRadius: circle ? null : widget.borderRadius,
        border: _focused ? Border.all(color: AppColors.focusRing, width: AppSize.focusRingWidth) : null,
      ),
      child: InkWell(
        key: widget.inkKey,
        borderRadius: circle ? null : widget.borderRadius,
        customBorder: widget.shape,
        onTap: widget.onTap,
        onFocusChange: (focused) => setState(() => _focused = focused),
        child: widget.child,
      ),
    );
  }
}
