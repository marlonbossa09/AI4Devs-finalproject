import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/team_entities.dart';
import 'shared_activity_tile.dart';

/// The logbook of a colleague for one date, READ-ONLY (M4-01). It has no edit field and no action: the summary is
/// plain text and every activity is a [SharedActivityTile], which cannot do anything either.
class PeerLogbookView extends StatelessWidget {
  const PeerLogbookView({super.key, required this.logbook, required this.ownerName});

  final PeerLogbook logbook;
  final String ownerName;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('peer-logbook'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(ownerName, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
            Text(formatLongDate(logbook.date), style: const TextStyle(fontSize: 12.5, color: AppColors.textSoft)),
            StatusPill(label: logbook.closed ? 'Cerrada' : 'Abierta', kind: logbook.closed ? PillKind.done : PillKind.progress),
          ],
        ),
        const SizedBox(height: 4),
        const Text(
          'Solo lectura: esta bitácora no se puede modificar desde aquí.',
          key: Key('peer-readonly-note'),
          style: TextStyle(fontSize: 11, color: AppColors.textFaint),
        ),
        const SizedBox(height: 16),
        const FieldCaption('Resumen de la jornada'),
        const SizedBox(height: 6),
        Text(
          logbook.summary.trim().isEmpty ? 'Sin resumen.' : logbook.summary,
          key: const Key('peer-summary'),
          style: TextStyle(fontSize: 13, height: 1.55, color: logbook.summary.trim().isEmpty ? AppColors.textFaint : AppColors.textBody),
        ),
        const SizedBox(height: 18),
        const FieldCaption('Actividades'),
        const SizedBox(height: 8),
        if (logbook.activities.isEmpty)
          const EmptyState('No hay actividades que mostrar en esta bitácora.', key: Key('peer-no-activities'))
        else
          for (final activity in logbook.activities)
            SharedActivityTile(
              activity: activity,
              plannings: [for (final p in logbook.plannings) if (p.activityId == activity.id) p],
              progress: [for (final a in logbook.progress) if (a.activityId == activity.id) a],
            ),
      ],
    );
  }
}

/// Small section caption.
class FieldCaption extends StatelessWidget {
  const FieldCaption(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) =>
      Text(text, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: AppColors.textLabel));
}
