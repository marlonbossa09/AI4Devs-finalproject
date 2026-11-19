import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/team_entities.dart';
import 'shared_activity_tile.dart';

/// The logbook of a colleague for one date, READ-ONLY (M4-01). It has no edit field and no action: the summary is
/// plain text and every activity is a [SharedActivityTile], which cannot do anything either.
///
/// The name of the person is already in the header of the panel that holds this view, so it is not repeated as text
/// here; a screen reader still hears whose logbook it is, which date, and whether it is open or closed.
class PeerLogbookView extends StatelessWidget {
  const PeerLogbookView({super.key, required this.logbook, required this.ownerName});

  final PeerLogbook logbook;
  final String ownerName;

  @override
  Widget build(BuildContext context) {
    final summaryEmpty = logbook.summary.trim().isEmpty;
    return Column(
      key: const Key('peer-logbook'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // A polite live region: the logbook appears after the user asks for it, and a screen reader says what arrived.
        Semantics(
          liveRegion: true,
          label: 'Bitácora de $ownerName del ${formatLongDate(logbook.date)}, ${logbook.closed ? 'cerrada' : 'abierta'}.',
          excludeSemantics: true,
          child: Wrap(
            spacing: AppSpace.md,
            runSpacing: AppSpace.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                formatLongDate(logbook.date),
                style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink),
              ),
              StatusPill(
                label: logbook.closed ? 'Cerrada' : 'Abierta',
                kind: logbook.closed ? PillKind.done : PillKind.progress,
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.xs),
        const Row(
          children: [
            ExcludeSemantics(child: Icon(Icons.lock_outline, size: 14, color: AppColors.textSoft)),
            SizedBox(width: AppSpace.xs + 2),
            Expanded(
              child: Text(
                'Solo lectura: esta bitácora no se puede modificar desde aquí.',
                key: Key('peer-readonly-note'),
                style: TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpace.lg),
        const FieldCaption('Resumen de la jornada'),
        const SizedBox(height: AppSpace.xs + 2),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(AppSpace.md),
          decoration: BoxDecoration(
            color: AppColors.panelFooter,
            border: Border.all(color: AppColors.border),
            borderRadius: BorderRadius.circular(AppRadius.control),
          ),
          child: Text(
            summaryEmpty ? 'Sin resumen.' : logbook.summary,
            key: const Key('peer-summary'),
            style: TextStyle(
              fontSize: AppType.body,
              height: 1.5,
              color: summaryEmpty ? AppColors.textSoft : AppColors.textBody,
            ),
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        const FieldCaption('Actividades'),
        if (logbook.activities.isEmpty)
          const EmptyState('No hay actividades que mostrar en esta bitácora.', key: Key('peer-no-activities'))
        else
          for (var i = 0; i < logbook.activities.length; i++)
            SharedActivityTile(
              first: i == 0,
              activity: logbook.activities[i],
              plannings: [for (final p in logbook.plannings) if (p.activityId == logbook.activities[i].id) p],
              progress: [for (final a in logbook.progress) if (a.activityId == logbook.activities[i].id) a],
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
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpace.xs),
    child: Text(text, style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w800, color: AppColors.textLabel)),
  );
}
