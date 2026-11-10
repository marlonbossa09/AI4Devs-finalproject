import 'package:flutter/material.dart';

import '../../../../core/widgets/kind_tag.dart';

/// Colors of a reactivation. They differ from the original planning (teal), the planned continuation
/// (terracotta), the progress (blue) and the unplanned identification (violet).
class ReactivationColors {
  const ReactivationColors._();

  static const background = Color(0xFFFBEAF2);
  static const foreground = Color(0xFFA6396B);
  static const border = Color(0xFFF0CFE0);
}

/// Tag "Reactivación": an ordinary progress entry never carries it, so the two cannot be mistaken.
class ReactivationTag extends StatelessWidget {
  const ReactivationTag({super.key});

  @override
  Widget build(BuildContext context) {
    return const KindTag(
      'Reactivación',
      icon: Icons.replay,
      color: ReactivationColors.foreground,
      background: ReactivationColors.background,
    );
  }
}
