import 'package:flutter/material.dart';

import '../../../../core/widgets/kind_tag.dart';

/// Colors of a planned continuation. They differ from the original planning (teal), the progress
/// (blue) and the unplanned identification (violet), so the four never look alike.
class ContinuationColors {
  const ContinuationColors._();

  static const background = Color(0xFFFCEFE4);
  static const foreground = Color(0xFFA85A22);
  static const border = Color(0xFFF3D9C2);
}

/// Tag "Continuación planificada": it always carries its name, so it does not rely on color alone.
class ContinuationTag extends StatelessWidget {
  const ContinuationTag({super.key});

  @override
  Widget build(BuildContext context) {
    return const KindTag(
      'Continuación planificada',
      icon: Icons.event_repeat_outlined,
      color: ContinuationColors.foreground,
      background: ContinuationColors.background,
    );
  }
}
