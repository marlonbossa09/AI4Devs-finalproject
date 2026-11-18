import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../../logbook/presentation/widgets/activity_tile.dart' show pillKind, statusLabel;
import '../../../logbook/presentation/widgets/marked_tag.dart';
import '../../../logbook/presentation/widgets/origin_tag.dart';
import '../../domain/entities/team_entities.dart';

/// One activity of another person, READ-ONLY. There is no button of any kind: nothing here can register, correct,
/// reactivate, mark or close anything, and nothing opens a detail (a neutral reference stays neutral wherever the
/// reader goes).
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
  });

  final SharedActivity activity;

  /// What the person foresaw for the day shown, for this activity.
  final List<PeerPlanning> plannings;

  /// What the person did in the day shown, for this activity.
  final List<PeerProgress> progress;

  /// Whether each planning and progress line also shows its date (the history shows several days).
  final bool showDates;

  @override
  Widget build(BuildContext context) {
    final neutral = activity.isNeutral;
    return Container(
      key: Key('shared-activity-${activity.id}'),
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: neutral ? const Color(0xFFF7F8FA) : Colors.white,
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: neutral ? const Color(0xFFD7DCE4) : AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (neutral) ...[
            const Row(
              children: [
                Icon(Icons.link, size: 16, color: AppColors.textSoft),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    neutralActivityLabel,
                    key: Key('neutral-label'),
                    style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: AppColors.textSoft),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Continúa un trabajo anterior. Su título no se muestra.',
              key: Key('neutral-note'),
              style: TextStyle(fontSize: 11, color: AppColors.textFaint),
            ),
          ] else ...[
            Wrap(
              spacing: 8,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(activity.title!, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
                if (activity.origin != null) OriginTag(origin: activity.origin!),
                if (activity.status != null)
                  StatusPill(label: statusLabel(activity.status!), kind: pillKind(activity.status!)),
                if (activity.isMarked) const MarkedTag(),
              ],
            ),
            if (activity.isMarked) ...[
              const SizedBox(height: 4),
              Text(
                'Motivo de la marca: ${activity.markReason}',
                style: const TextStyle(fontSize: 11, color: AppColors.textSoft),
              ),
            ],
          ],
          for (final p in plannings) ...[
            const SizedBox(height: 8),
            _Line(
              icon: Icons.event_note_outlined,
              label: p.type == PlanningType.original ? 'Planificada' : 'Continuación planificada',
              text: p.description,
              date: showDates ? p.date : null,
            ),
          ],
          for (final a in progress) ...[
            const SizedBox(height: 8),
            _Line(
              icon: Icons.check_circle_outline,
              label: 'Avance',
              text: a.description,
              date: showDates ? a.date : null,
              status: a.status,
              blockReason: a.blockReason,
            ),
          ],
        ],
      ),
    );
  }
}

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
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 14, color: AppColors.textSoft),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 4,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(label, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: AppColors.textSoft)),
                  if (date != null)
                    Text(formatShortDate(date!), style: const TextStyle(fontSize: 10.5, color: AppColors.textFaint)),
                  if (status != null) StatusPill(label: statusLabel(status!), kind: pillKind(status!)),
                ],
              ),
              if (text.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 2), child: Text(text, style: const TextStyle(fontSize: 12.5, height: 1.45))),
              if (blockReason != null && blockReason!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('Motivo del bloqueo: $blockReason', style: const TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
