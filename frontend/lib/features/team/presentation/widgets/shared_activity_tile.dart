import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../../logbook/presentation/widgets/activity_tile.dart' show pillKind, statusLabel;
import '../../../logbook/presentation/widgets/marked_tag.dart';
import '../../../logbook/presentation/widgets/origin_tag.dart';
import '../../domain/entities/team_entities.dart';

/// One activity of another person, READ-ONLY, as a compact row of a list (it draws its own top divider unless it is the
/// [first]). There is no button of any kind: nothing here can register, correct, reactivate, mark or close anything, and
/// nothing opens a detail (a neutral reference stays neutral wherever the reader goes).
///
/// - `full` form: title, origin tag, current status (only when the server reports it) and, if it was marked as
///   registered by mistake, the mark with its reason.
/// - `neutral` form: ONLY the fixed label "Actividad en continuidad". There is no title, no origin, no status, no
///   mark and no date to show; the tile does not even have somewhere to put them.
class SharedActivityTile extends StatelessWidget {
  const SharedActivityTile({
    super.key,
    required this.activity,
    this.plannings = const [],
    this.progress = const [],
    this.showDates = false,
    this.first = false,
  });

  final SharedActivity activity;

  /// What the person foresaw for the day shown, for this activity.
  final List<PeerPlanning> plannings;

  /// What the person did in the day shown, for this activity.
  final List<PeerProgress> progress;

  /// Whether each planning and progress line also shows its date (the history shows several days).
  final bool showDates;

  /// The first row of a list has no divider above it.
  final bool first;

  @override
  Widget build(BuildContext context) {
    final neutral = activity.isNeutral;
    final unplanned = activity.origin == ActivityOrigin.unplanned;
    final (background, foreground, icon) = neutral
        ? (AppColors.recordedBackground, AppColors.recordedText, Icons.link)
        : unplanned
        ? (UnplannedColors.background, UnplannedColors.foreground, Icons.bolt)
        : (AppColors.progressBackground, AppColors.progressText, Icons.event_note_outlined);
    return Container(
      key: Key('shared-activity-${activity.id}'),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ExcludeSemantics(
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(AppRadius.control)),
              child: Icon(icon, size: 18, color: foreground),
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (neutral) ...[
                  const Text(
                    neutralActivityLabel,
                    key: Key('neutral-label'),
                    style: TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.textSoft),
                  ),
                  const SizedBox(height: AppSpace.xs),
                  const Text(
                    'Continúa un trabajo anterior. Su título no se muestra.',
                    key: Key('neutral-note'),
                    style: TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
                  ),
                ] else ...[
                  Wrap(
                    spacing: AppSpace.sm,
                    runSpacing: AppSpace.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        activity.title!,
                        style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink),
                      ),
                      if (activity.origin != null) OriginTag(origin: activity.origin!),
                      if (activity.status != null)
                        StatusPill(label: statusLabel(activity.status!), kind: pillKind(activity.status!)),
                      if (activity.isMarked) const MarkedTag(),
                    ],
                  ),
                  if (activity.isMarked) ...[
                    const SizedBox(height: AppSpace.xs),
                    Text(
                      'Motivo de la marca: ${activity.markReason}',
                      style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
                    ),
                  ],
                ],
                for (final p in plannings)
                  _Line(
                    icon: Icons.event_note_outlined,
                    label: p.type == PlanningType.original ? 'Planificada' : 'Continuación planificada',
                    text: p.description,
                    date: showDates ? p.date : null,
                  ),
                for (final a in progress)
                  _Line(
                    icon: Icons.check_circle_outline,
                    label: 'Avance',
                    text: a.description,
                    date: showDates ? a.date : null,
                    status: a.status,
                    blockReason: a.blockReason,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// What the person foresaw (a planning) or did (a progress entry) for the activity, told with its own word.
class _Line extends StatelessWidget {
  const _Line({required this.icon, required this.label, required this.text, this.date, this.status, this.blockReason});

  final IconData icon;
  final String label;
  final String text;
  final DateTime? date;
  final ActivityStatus? status;
  final String? blockReason;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpace.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: ExcludeSemantics(child: Icon(icon, size: 14, color: AppColors.textSoft)),
          ),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpace.sm,
                  runSpacing: AppSpace.xs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(label, style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w800, color: AppColors.textSoft)),
                    if (date != null)
                      Text(formatShortDate(date!), style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
                    if (status != null) StatusPill(label: statusLabel(status!), kind: pillKind(status!)),
                  ],
                ),
                if (text.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(text, style: const TextStyle(fontSize: AppType.body, height: 1.45, color: AppColors.textBody)),
                  ),
                if (blockReason != null && blockReason!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      'Motivo del bloqueo: $blockReason',
                      style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.blockedText),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
