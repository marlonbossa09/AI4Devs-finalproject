import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/focus_ring.dart';
import '../../domain/entities/logbook_entities.dart';

/// Background and text colors of an activity status (the same ones as its pill).
(Color, Color) statusColors(ActivityStatus status) => switch (status) {
  ActivityStatus.pending => (AppColors.pendingBackground, AppColors.pendingText),
  ActivityStatus.inProgress => (AppColors.progressBackground, AppColors.progressText),
  ActivityStatus.blocked => (AppColors.blockedBackground, AppColors.blockedText),
  ActivityStatus.completed => (AppColors.doneBackground, AppColors.doneText),
};

/// A selectable option with the colors of a status (or neutral when [colors] is null). Used where
/// the user picks a status: the progress form and the list filter. The selected one is told by a check, a thicker border and
/// its color, never by color alone; it is at least 40 px tall and shows the keyboard focus ring.
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
    final (background, text) = colors ?? (AppColors.primarySoft, AppColors.primary);
    final radius = BorderRadius.circular(AppRadius.control);
    return Semantics(
      button: true,
      selected: selected,
      enabled: onTap != null,
      label: label,
      excludeSemantics: true,
      onTap: onTap,
      child: FocusRingInk(
        borderRadius: radius,
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: AppSize.minTouch),
          padding: const EdgeInsets.symmetric(horizontal: AppSpace.md),
          decoration: BoxDecoration(
            color: selected ? background : AppColors.white,
            borderRadius: radius,
            border: Border.all(color: selected ? text : AppColors.fieldBorder, width: selected ? 1.5 : 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (selected) ...[Icon(Icons.check, size: 16, color: text), const SizedBox(width: AppSpace.xs + 2)],
              Flexible(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: AppType.caption,
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
