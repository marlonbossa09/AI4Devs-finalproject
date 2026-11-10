import 'package:flutter/material.dart';

import '../../../../core/widgets/kind_tag.dart';

/// Colors of the audit (M3-07). Violet, apart from planning (teal) and execution (blue): the audit is not the
/// history of the work, it is the record of changes made to the records.
class AuditColors {
  const AuditColors._();

  static const background = Color(0xFFF0ECFA);
  static const foreground = Color(0xFF5B3FA6);
  static const border = Color(0xFFDDD5F2);
}

/// Says, without relying on color alone, that a block belongs to the audit and not to the work history.
class AuditTag extends StatelessWidget {
  const AuditTag({super.key});

  @override
  Widget build(BuildContext context) {
    return const KindTag(
      'Auditoría',
      icon: Icons.history_edu_outlined,
      color: AuditColors.foreground,
      background: AuditColors.background,
    );
  }
}
