import 'package:flutter/material.dart';

import '../../../../core/widgets/kind_tag.dart';

/// Colors of an activity marked as registered by mistake (RN-59). Neutral grey: it is not a status
/// (it is never a fifth one) and it must not be mistaken for Bloqueada, which is red.
class MarkedColors {
  const MarkedColors._();

  static const background = Color(0xFFEEF0F4);
  static const foreground = Color(0xFF5B677A);
  static const border = Color(0xFFD7DCE4);
}

/// Says, without relying on color alone, that an activity was marked as registered by mistake.
class MarkedTag extends StatelessWidget {
  const MarkedTag({super.key});

  @override
  Widget build(BuildContext context) {
    return const KindTag(
      'Registrada por error',
      icon: Icons.report_gmailerrorred_outlined,
      color: MarkedColors.foreground,
      background: MarkedColors.background,
    );
  }
}
