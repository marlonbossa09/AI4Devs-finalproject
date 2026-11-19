import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../domain/entities/logbook_entities.dart';

/// Colors used to tell an UNPLANNED activity apart from a planned one. They are deliberately not
/// those of any status pill: being unplanned is an identification, not a status (RN-20, CA-57).
class UnplannedColors {
  const UnplannedColors._();

  static const background = AppColors.unplannedBackground;
  static const foreground = AppColors.unplannedText;
}

/// Small tag "No planificada". It is shown only for activities registered without a prior planning;
/// planned activities carry no tag.
class OriginTag extends StatelessWidget {
  const OriginTag({super.key, required this.origin});

  final ActivityOrigin origin;

  @override
  Widget build(BuildContext context) {
    if (origin != ActivityOrigin.unplanned) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm, vertical: AppSpace.xs - 1),
      decoration: BoxDecoration(color: UnplannedColors.background, borderRadius: BorderRadius.circular(AppRadius.control - 2)),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.bolt, size: 14, color: UnplannedColors.foreground),
          SizedBox(width: AppSpace.xs - 1),
          Flexible(
            child: Text(
              'No planificada',
              style: TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w800, color: UnplannedColors.foreground),
            ),
          ),
        ],
      ),
    );
  }
}
