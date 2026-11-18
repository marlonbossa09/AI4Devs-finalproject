import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../../logbook/presentation/widgets/activity_tile.dart' show pillKind, statusLabel;
import '../../../logbook/presentation/widgets/marked_tag.dart';
import '../../../logbook/presentation/widgets/origin_tag.dart';
import '../../../team/domain/entities/team_entities.dart';
import '../../domain/entities/supervision_entities.dart';

/// Short, readable names for the reasons an activity is in the view (RN-47).
String inclusionReasonLabel(InclusionReason reason) => switch (reason) {
  InclusionReason.plannedInPeriod => 'Planificada en el período',
  InclusionReason.withProgressInPeriod => 'Con avances en el período',
  InclusionReason.pendingAtCut => 'Pendiente al corte',
};

/// The minimal reference, in the same shape wherever it appears (the supervision list and the activity history). It is
/// told apart from a full activity by its tag and its note (RN-89), carries ONLY the fields of the contract and offers
/// nothing that opens more than the server gives.
class MinimalReferenceBlock extends StatelessWidget {
  const MinimalReferenceBlock({super.key, required this.reference, required this.ownerName});

  final MinimalReference reference;
  final String ownerName;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: Key('minimal-reference-${reference.activity.id}'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            const KindTag('Referencia mínima', icon: Icons.link_outlined, color: Color(0xFF5B677A), background: Color(0xFFEEF0F4)),
            Text(ownerName, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
          ],
        ),
        const SizedBox(height: 8),
        const Text('Iniciada en otro equipo', key: Key('minimal-origin'), style: TextStyle(fontSize: 12, color: AppColors.textBody)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            const Text('Estado actual', style: TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
            StatusPill(label: statusLabel(reference.currentStatus), kind: pillKind(reference.currentStatus)),
          ],
        ),
        if (reference.lastProgressDate != null) ...[
          const SizedBox(height: 6),
          Text(
            'Último avance: ${formatShortDate(reference.lastProgressDate!)}',
            key: const Key('minimal-last-progress'),
            style: const TextStyle(fontSize: 11.5, color: AppColors.textSoft),
          ),
        ],
        const SizedBox(height: 8),
        const Text(
          'Solo una referencia: no incluye el título ni el historial de esta actividad.',
          key: Key('minimal-note'),
          style: TextStyle(fontSize: 11, color: AppColors.textFaint),
        ),
      ],
    );
  }
}

/// One element of the supervision view. Read-only: its only action opens the history of the activity (M4-04).
///
/// - Full activity: title, origin, mark, the reasons it is included and the status AT THE CUT; the current status is
///   shown apart and only when the server sends it.
/// - Neutral activity: only "Actividad en continuidad".
/// - Minimal reference: a [MinimalReferenceBlock].
///
/// When the server omits the status at the cut, the tile says it is not available; it does not infer one, and it does
/// not show the current status in its place.
class SupervisionItemTile extends StatelessWidget {
  const SupervisionItemTile({super.key, required this.item, required this.ownerName, required this.onOpen});

  final SupervisionItem item;
  final String ownerName;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final current = item;
    final neutral = item.activity.isNeutral;
    return Container(
      key: Key('supervision-item-${item.activity.id}'),
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
          if (current is MinimalReference)
            MinimalReferenceBlock(reference: current, ownerName: ownerName)
          else if (current is SupervisedActivity)
            ..._activity(current),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerLeft,
            child: SecondaryButton(
              key: Key('supervision-open-${item.activity.id}'),
              label: current is MinimalReference ? 'Ver referencia' : 'Ver historial',
              onPressed: onOpen,
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _activity(SupervisedActivity a) {
    final activity = a.activity;
    return [
      if (activity.isNeutral)
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
        )
      else
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(activity.title!, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
            if (activity.origin != null) OriginTag(origin: activity.origin!),
            if (activity.isMarked) const MarkedTag(),
          ],
        ),
      const SizedBox(height: 4),
      Text(ownerName, style: const TextStyle(fontSize: 12, color: AppColors.textSoft)),
      const SizedBox(height: 8),
      Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          for (final reason in a.reasons)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: AppColors.tealSoft, borderRadius: BorderRadius.circular(6)),
              child: Text(
                inclusionReasonLabel(reason),
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF276A67)),
              ),
            ),
        ],
      ),
      const SizedBox(height: 10),
      Wrap(
        spacing: 8,
        runSpacing: 6,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          const Text('Estado al corte', style: TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
          if (a.statusAtCut != null)
            StatusPill(label: statusLabel(a.statusAtCut!), kind: pillKind(a.statusAtCut!))
          else
            const Text('No disponible', key: Key('status-at-cut-unavailable'), style: TextStyle(fontSize: 11.5, color: AppColors.textFaint)),
        ],
      ),
      if (a.currentStatusIfDiffers != null) ...[
        const SizedBox(height: 6),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            const Text('Estado actual', key: Key('current-status-label'), style: TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
            StatusPill(label: statusLabel(a.currentStatusIfDiffers!), kind: pillKind(a.currentStatusIfDiffers!)),
          ],
        ),
      ],
    ];
  }
}

/// Totals of the period by status at the cut, and how many elements have no status at the cut. No person is ranked,
/// scored or compared: these are counts of activities.
class SupervisionTotals extends StatelessWidget {
  const SupervisionTotals({super.key, required this.page});

  final SupervisionPage page;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('supervision-totals'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final status in ActivityStatus.values)
              Container(
                key: Key('total-${status.name}'),
                width: 150,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: const Color(0xFFFAFBFD), borderRadius: BorderRadius.circular(11), border: Border.all(color: AppColors.border)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    StatusPill(label: statusLabel(status), kind: pillKind(status)),
                    const SizedBox(height: 8),
                    Text('${page.totals[status] ?? 0}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                  ],
                ),
              ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          'Sin estado al corte: ${page.withoutStatus.minimalReferences} referencias mínimas y ${page.withoutStatus.activities} actividades. '
          'No están en los totales de arriba.',
          key: const Key('without-status'),
          style: const TextStyle(fontSize: 11.5, height: 1.5, color: AppColors.textSoft),
        ),
      ],
    );
  }
}
