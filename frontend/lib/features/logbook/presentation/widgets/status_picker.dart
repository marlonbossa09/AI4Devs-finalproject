import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/fields.dart';
import '../../domain/entities/logbook_entities.dart';
import 'activity_tile.dart';
import 'status_choice.dart';

/// The four activity states as selectable options. They wrap onto several lines on narrow screens,
/// so the picker works the same on desktop, tablet and mobile.
class StatusPicker extends StatelessWidget {
  const StatusPicker({
    super.key,
    required this.selected,
    required this.onChanged,
    this.enabled = true,
    this.errorText,
    this.keyPrefix = 'progress-status',
    this.statuses = ActivityStatus.values,
    this.label = 'Estado en que queda la actividad *',
  });

  /// The options offered. A reactivation offers only the three that are not Completada.
  final List<ActivityStatus> statuses;

  /// The question the options answer.
  final String label;

  final ActivityStatus? selected;
  final ValueChanged<ActivityStatus> onChanged;
  final bool enabled;
  final String? errorText;

  /// Keys of the options are `<keyPrefix>-<status name>`.
  final String keyPrefix;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel(label),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final status in statuses)
              StatusChoice(
                key: Key('$keyPrefix-${status.name}'),
                label: statusLabel(status),
                colors: statusColors(status),
                selected: status == selected,
                onTap: enabled ? () => onChanged(status) : null,
              ),
          ],
        ),
        if (errorText != null) ...[
          const SizedBox(height: 6),
          Text(errorText!, style: const TextStyle(fontSize: 12, color: AppColors.error)),
        ],
      ],
    );
  }
}
