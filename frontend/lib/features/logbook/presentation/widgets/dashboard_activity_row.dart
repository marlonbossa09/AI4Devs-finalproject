import 'package:flutter/material.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/reactivation_rules.dart';
import 'activity_tile.dart' show pillKind, statusLabel;
import 'origin_tag.dart';

/// One activity of the dashboard list, compact: what it is, how it started, its CURRENT status and the actions the person
/// has on it. It shows no clock time and no duration, because nothing of the kind is recorded for an activity; the progress
/// entries and the planned continuations of the day are told in Mi bitácora, which is where the day is read in full.
///
/// The status is the current one (the last progress entry; Pendiente if there is none). It always travels as a word.
class DashboardActivityRow extends StatelessWidget {
  const DashboardActivityRow({
    super.key,
    required this.activity,
    this.planning,
    this.hasContinuation = false,
    this.hasProgress = false,
    this.blockReason,
    this.onRegisterProgress,
    this.onReactivate,
    this.onOpen,
    this.first = false,
  });

  final Activity activity;

  /// The ORIGINAL planning of the activity in the day being shown, if it has one there.
  final Planning? planning;

  /// Whether a continuation of the activity is planned for the day being shown.
  final bool hasContinuation;

  /// Whether progress of the activity was recorded in the day being shown.
  final bool hasProgress;

  /// The reason the activity is blocked, when it is (RN-24). It is told right under the description.
  final String? blockReason;

  /// Opens the progress form. Null when the day is closed (it has to be reopened first, RN-108).
  final VoidCallback? onRegisterProgress;
  final VoidCallback? onReactivate;
  final VoidCallback? onOpen;

  final bool first;

  @override
  Widget build(BuildContext context) {
    final unplanned = activity.origin == ActivityOrigin.unplanned;
    final done = activity.status == ActivityStatus.completed;
    // The activity is in this day only because a continuation was planned for it: its own planning belongs to another day.
    final continuationOnly = planning == null && hasContinuation && !hasProgress && !unplanned;
    final description = unplanned
        ? 'Registrada sin planificación previa.'
        : continuationOnly
            ? 'Continuación planificada para esta jornada. Origen: ${formatShortDate(activity.date)}.'
            : (planning?.description.isNotEmpty == true ? planning!.description : 'Sin descripción');
    final canReactivateIt = onReactivate != null && canReactivate(status: activity.status, marked: activity.marked);
    final mobile = ScreenSize.ofContext(context).isMobile;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ExcludeSemantics(
            child: Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: unplanned ? UnplannedColors.background : AppColors.progressBackground,
                borderRadius: BorderRadius.circular(AppRadius.control),
              ),
              child: Icon(
                done ? Icons.check : (unplanned ? Icons.bolt : Icons.event_note_outlined),
                size: 18,
                color: unplanned ? UnplannedColors.foreground : AppColors.progressText,
              ),
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpace.sm,
                  runSpacing: AppSpace.xs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(activity.title, style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink)),
                    // The type is always told in words: "No planificada" by its own tag, "Planificada" by a neutral one
                    KeyedSubtree(
                      key: Key('origin-${activity.id}'),
                      child: unplanned ? OriginTag(origin: activity.origin) : const _PlannedTag(),
                    ),
                    // On a phone the status goes right after the title, so it is read with it; on a wider screen it sits at the end of the row.
                    if (mobile) KeyedSubtree(key: Key('status-${activity.id}'), child: _pill()),
                  ],
                ),
                const SizedBox(height: AppSpace.xs),
                Text(
                  description,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
                ),
                if (blockReason != null)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpace.xs),
                    child: Text(
                      'Motivo del bloqueo: $blockReason',
                      key: Key('block-reason-${activity.id}'),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.blockedText),
                    ),
                  ),
                if (onOpen != null || onRegisterProgress != null || canReactivateIt)
                  Wrap(
                    spacing: AppSpace.md,
                    children: [
                      if (onOpen != null)
                        LinkButton(key: Key('activity-open-${activity.id}'), label: 'Ver detalle', onPressed: onOpen),
                      if (onRegisterProgress != null)
                        LinkButton(
                          key: Key('progress-action-${activity.id}'),
                          label: '+ Registrar avance',
                          onPressed: onRegisterProgress,
                        ),
                      if (canReactivateIt)
                        LinkButton(key: Key('reactivation-action-${activity.id}'), label: 'Reactivar', onPressed: onReactivate),
                    ],
                  ),
              ],
            ),
          ),
          if (!mobile) ...[
            const SizedBox(width: AppSpace.md),
            KeyedSubtree(key: Key('status-${activity.id}'), child: _pill()),
          ],
        ],
      ),
    );
  }

  Widget _pill() => StatusPill(label: statusLabel(activity.status), kind: pillKind(activity.status));
}

/// "Planificada": how the activity started. Neutral, because it is an identification and not a status (RN-20).
class _PlannedTag extends StatelessWidget {
  const _PlannedTag();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm, vertical: AppSpace.xs - 1),
      decoration: BoxDecoration(color: AppColors.recordedBackground, borderRadius: BorderRadius.circular(AppRadius.control - 2)),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.event_note_outlined, size: 14, color: AppColors.recordedText),
          SizedBox(width: AppSpace.xs - 1),
          Text(
            'Planificada',
            style: TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w800, color: AppColors.recordedText),
          ),
        ],
      ),
    );
  }
}
