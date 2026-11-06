import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../domain/entities/logbook_entities.dart';

String statusLabel(ActivityStatus status) => switch (status) {
  ActivityStatus.pending => 'Pendiente',
  ActivityStatus.inProgress => 'En progreso',
  ActivityStatus.blocked => 'Bloqueada',
  ActivityStatus.completed => 'Completada',
};

PillKind pillKind(ActivityStatus status) => switch (status) {
  ActivityStatus.pending => PillKind.pending,
  ActivityStatus.inProgress => PillKind.progress,
  ActivityStatus.blocked => PillKind.blocked,
  ActivityStatus.completed => PillKind.done,
};

/// One activity row: icon, title, planned description, when it was planned, and its status
/// (`.activity`). The status is the CURRENT one; the planning is shown as "Planificada" so it is
/// not mistaken for a progress entry.
class ActivityTile extends StatelessWidget {
  const ActivityTile({super.key, required this.activity, this.planning, this.first = false});

  final Activity activity;
  final Planning? planning;

  /// The first row has no top border.
  final bool first;

  @override
  Widget build(BuildContext context) {
    final description = planning?.description ?? '';
    final planned = planning;
    final done = activity.status == ActivityStatus.completed;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 17),
      decoration: BoxDecoration(
        border: first ? null : const Border(top: BorderSide(color: AppColors.divider)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 37,
            height: 37,
            decoration: BoxDecoration(
              color: const Color(0xFFE7F2FA),
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(
              done ? Icons.check : Icons.event_note_outlined,
              size: 18,
              color: const Color(0xFF4C829D),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  activity.title,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 5),
                Text(
                  description.isEmpty ? 'Sin descripción' : description,
                  style: const TextStyle(fontSize: 11, height: 1.65, color: AppColors.textSoft),
                ),
                const SizedBox(height: 9),
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 9,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.schedule, size: 12, color: AppColors.textFaint),
                        const SizedBox(width: 4),
                        Text(
                          planned == null ? 'Planificada' : 'Planificada ${formatTime(planned.createdAt)}',
                          style: const TextStyle(fontSize: 10, color: AppColors.textFaint),
                        ),
                      ],
                    ),
                    const _Dot(),
                    Text(
                      formatDate(activity.date),
                      style: const TextStyle(fontSize: 10, color: AppColors.textFaint),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          KeyedSubtree(
            key: Key('status-${activity.id}'),
            child: StatusPill(label: statusLabel(activity.status), kind: pillKind(activity.status)),
          ),
        ],
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot();

  @override
  Widget build(BuildContext context) => Container(
    width: 3,
    height: 3,
    decoration: const BoxDecoration(color: Color(0xFFBDC7D2), shape: BoxShape.circle),
  );
}
