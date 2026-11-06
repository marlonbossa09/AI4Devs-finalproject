import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/entities/logbook_entities.dart';

/// Background and text colors of an activity status (the same ones as its pill).
(Color, Color) statusColors(ActivityStatus status) => switch (status) {
  ActivityStatus.pending => (AppColors.pendingBackground, AppColors.pendingText),
  ActivityStatus.inProgress => (AppColors.progressBackground, AppColors.progressText),
  ActivityStatus.blocked => (AppColors.blockedBackground, AppColors.blockedText),
  ActivityStatus.completed => (AppColors.doneBackground, AppColors.doneText),
};

/// A selectable option with the colors of a status (or neutral when [colors] is null). Used where
/// the user picks a status: the progress form and the list filter.
class StatusChoice extends StatelessWidget {
  const StatusChoice({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
    this.colors,
  });

  final String label;
  final (Color, Color)? colors;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final (background, text) = colors ?? (AppColors.tealSoft, AppColors.teal);
    return Semantics(
      button: true,
      selected: selected,
      enabled: onTap != null,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            color: selected ? background : AppColors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: selected ? text : AppColors.fieldBorder, width: selected ? 1.5 : 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (selected) ...[Icon(Icons.check, size: 14, color: text), const SizedBox(width: 6)],
              ExcludeSemantics(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                    color: selected ? text : AppColors.textBody,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
