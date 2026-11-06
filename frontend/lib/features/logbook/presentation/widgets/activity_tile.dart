import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../domain/entities/logbook_entities.dart';
import 'origin_tag.dart';

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
/// not mistaken for a progress entry. The progress entries recorded in the shown day appear
/// apart, each with the status it had when it was recorded.
class ActivityTile extends StatelessWidget {
  const ActivityTile({
    super.key,
    required this.activity,
    this.planning,
    this.progress = const [],
    this.onRegisterProgress,
    this.onOpen,
    this.first = false,
  });

  final Activity activity;
  final Planning? planning;

  /// Progress entries of [activity] recorded in the day being shown.
  final List<Progress> progress;

  /// Opens the progress form for this activity. Not offered for an activity marked as an error.
  final VoidCallback? onRegisterProgress;

  /// Opens the activity detail (M2-07).
  final VoidCallback? onOpen;

  /// The first row has no top border.
  final bool first;

  @override
  Widget build(BuildContext context) {
    final unplanned = activity.origin == ActivityOrigin.unplanned;
    // An unplanned activity has no planning: its text is never invented (IR-16)
    final description = unplanned ? 'Registrada sin planificación previa.' : (planning?.description ?? '');
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
              color: unplanned ? UnplannedColors.background : const Color(0xFFE7F2FA),
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(
              done ? Icons.check : (unplanned ? Icons.bolt : Icons.event_note_outlined),
              size: 18,
              color: unplanned ? UnplannedColors.foreground : const Color(0xFF4C829D),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      activity.title,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
                    ),
                    KeyedSubtree(key: Key('origin-${activity.id}'), child: OriginTag(origin: activity.origin)),
                  ],
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
                          unplanned
                              ? 'Registrada ${formatTime(activity.createdAt)}'
                              : (planned == null ? 'Planificada' : 'Planificada ${formatTime(planned.createdAt)}'),
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
                if (progress.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  for (final entry in progress) _ProgressLine(key: Key('progress-entry-${entry.id}'), entry: entry),
                ],
                if (onOpen != null || (onRegisterProgress != null && !activity.marked)) ...[
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 12,
                    children: [
                      if (onOpen != null)
                        LinkButton(key: Key('activity-open-${activity.id}'), label: 'Ver detalle', onPressed: onOpen),
                      if (onRegisterProgress != null && !activity.marked)
                        LinkButton(
                          key: Key('progress-action-${activity.id}'),
                          label: '+ Registrar avance',
                          onPressed: onRegisterProgress,
                        ),
                    ],
                  ),
                ],
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

/// One recorded progress entry: the status it had, its description and, if blocked, the reason.
class _ProgressLine extends StatelessWidget {
  const _ProgressLine({super.key, required this.entry});

  final Progress entry;

  @override
  Widget build(BuildContext context) {
    final reason = entry.blockReason;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: Icon(Icons.trending_up, size: 13, color: AppColors.textFaint),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: 'Avance · ${statusLabel(entry.status)}: ',
                        style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.textBody),
                      ),
                      TextSpan(text: entry.description),
                    ],
                  ),
                  style: const TextStyle(fontSize: 11, height: 1.55, color: AppColors.textSoft),
                ),
                if (reason != null && reason.isNotEmpty)
                  Text(
                    'Motivo del bloqueo: $reason',
                    style: const TextStyle(fontSize: 11, height: 1.55, color: AppColors.blockedText),
                  ),
              ],
            ),
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
