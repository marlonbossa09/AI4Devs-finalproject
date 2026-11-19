import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/widgets/stat_card.dart';
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

/// Width of a row of the list from which its status block sits beside its content instead of under it.
const double _wideRowMinWidth = 720;

/// Width of the status block when it sits beside the content.
const double _statusBlockWidth = 260;

/// One line of a status block: what the status is ("Estado al corte", "Estado actual"), told in words and with its own icon,
/// and then the status itself as a pill. The two are told apart by their words, never by color alone. [labelKey] marks the
/// label for tests and automation.
class StatusLine extends StatelessWidget {
  const StatusLine({super.key, required this.label, required this.icon, required this.status, this.labelKey, this.unavailableKey});

  final String label;
  final IconData icon;

  /// The status to show; null says that the server did not send it ("No disponible"), it is never inferred.
  final ActivityStatus? status;
  final Key? labelKey;
  final Key? unavailableKey;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpace.sm,
      runSpacing: AppSpace.xs,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 110),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ExcludeSemantics(child: Icon(icon, size: 14, color: AppColors.textSoft)),
              const SizedBox(width: AppSpace.xs + 2),
              Flexible(
                child: Text(label, key: labelKey, style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
              ),
            ],
          ),
        ),
        if (status != null)
          StatusPill(label: statusLabel(status!), kind: pillKind(status!))
        else
          Text('No disponible', key: unavailableKey, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
      ],
    );
  }
}

/// A soft box that groups status lines, so that the status at the cut and the current one read as one unit.
class StatusBlock extends StatelessWidget {
  const StatusBlock({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm + 2),
      decoration: BoxDecoration(
        color: AppColors.panelFooter,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(AppRadius.control),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: AppSpace.sm),
                child: Divider(height: 1, thickness: 1, color: AppColors.divider),
              ),
            children[i],
          ],
        ],
      ),
    );
  }
}

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
          spacing: AppSpace.sm,
          runSpacing: AppSpace.xs + 2,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            const KindTag(
              'Referencia mínima',
              icon: Icons.link_outlined,
              color: AppColors.recordedText,
              background: AppColors.recordedBackground,
            ),
            Text(ownerName, style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink)),
          ],
        ),
        const SizedBox(height: AppSpace.sm),
        const Text('Iniciada en otro equipo', key: Key('minimal-origin'), style: TextStyle(fontSize: AppType.caption, color: AppColors.textBody)),
        const SizedBox(height: AppSpace.sm),
        Wrap(
          spacing: AppSpace.lg,
          runSpacing: AppSpace.xs + 2,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            StatusLine(label: 'Estado actual', icon: Icons.update, status: reference.currentStatus),
            if (reference.lastProgressDate != null)
              Text(
                'Último avance: ${formatShortDate(reference.lastProgressDate!)}',
                key: const Key('minimal-last-progress'),
                style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
              ),
          ],
        ),
        const SizedBox(height: AppSpace.sm),
        const Text(
          'Solo una referencia: no incluye el título ni el historial de esta actividad.',
          key: Key('minimal-note'),
          style: TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
        ),
      ],
    );
  }
}

/// One element of the supervision view, as a dense row of a list (it draws its own top divider unless it is the [first]).
/// Read-only: its only action opens the history of the activity (M4-04).
///
/// - Full activity: title, origin, mark, who, the reasons it is included and a status block with the status AT THE CUT; the
///   current status is a second line of that block, apart, and only when the server sends it.
/// - Neutral activity: only "Actividad en continuidad".
/// - Minimal reference: a [MinimalReferenceBlock].
///
/// When the server omits the status at the cut, the tile says it is not available; it does not infer one, and it does not
/// show the current status in its place.
class SupervisionItemTile extends StatelessWidget {
  const SupervisionItemTile({super.key, required this.item, required this.ownerName, required this.onOpen, this.first = false});

  final SupervisionItem item;
  final String ownerName;
  final VoidCallback onOpen;
  final bool first;

  @override
  Widget build(BuildContext context) {
    final current = item;
    final neutral = item.activity.isNeutral;
    final unplanned = item.activity.origin == ActivityOrigin.unplanned;
    final (background, foreground, icon) = current is MinimalReference || neutral
        ? (AppColors.recordedBackground, AppColors.recordedText, Icons.link)
        : unplanned
        ? (UnplannedColors.background, UnplannedColors.foreground, Icons.bolt)
        : (AppColors.progressBackground, AppColors.progressText, Icons.event_note_outlined);
    final link = LinkButton(
      key: Key('supervision-open-${item.activity.id}'),
      label: current is MinimalReference ? 'Ver referencia' : 'Ver historial',
      onPressed: onOpen,
    );

    return Container(
      key: Key('supervision-item-${item.activity.id}'),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final wide = constraints.maxWidth >= _wideRowMinWidth && current is SupervisedActivity;
          final main = current is MinimalReference
              ? MinimalReferenceBlock(reference: current, ownerName: ownerName)
              : _Main(item: current as SupervisedActivity, ownerName: ownerName);
          final status = current is SupervisedActivity ? _statusBlock(current) : null;
          return Row(
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
              if (wide) ...[
                Expanded(child: main),
                const SizedBox(width: AppSpace.md),
                SizedBox(width: _statusBlockWidth, child: status),
                const SizedBox(width: AppSpace.sm),
                link,
              ] else
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      main,
                      if (status != null) ...[const SizedBox(height: AppSpace.md), status],
                      Padding(padding: const EdgeInsets.only(top: AppSpace.xs), child: link),
                    ],
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  /// The status AT THE CUT, and apart from it the current status when the server sends it.
  Widget _statusBlock(SupervisedActivity a) {
    return StatusBlock(
      children: [
        StatusLine(
          label: 'Estado al corte',
          icon: Icons.flag_outlined,
          status: a.statusAtCut,
          unavailableKey: const Key('status-at-cut-unavailable'),
        ),
        if (a.currentStatusIfDiffers != null)
          StatusLine(
            label: 'Estado actual',
            icon: Icons.update,
            status: a.currentStatusIfDiffers,
            labelKey: const Key('current-status-label'),
          ),
      ],
    );
  }
}

/// Title, tags, who and why the activity is in the view.
class _Main extends StatelessWidget {
  const _Main({required this.item, required this.ownerName});

  final SupervisedActivity item;
  final String ownerName;

  @override
  Widget build(BuildContext context) {
    final activity = item.activity;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (activity.isNeutral)
          const Text(
            neutralActivityLabel,
            key: Key('neutral-label'),
            style: TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.textSoft),
          )
        else
          Wrap(
            spacing: AppSpace.sm,
            runSpacing: AppSpace.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(activity.title!, style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink)),
              if (activity.origin != null) OriginTag(origin: activity.origin!),
              if (activity.isMarked) const MarkedTag(),
            ],
          ),
        const SizedBox(height: AppSpace.xs),
        Row(
          children: [
            const ExcludeSemantics(child: Icon(Icons.person_outline, size: 14, color: AppColors.textSoft)),
            const SizedBox(width: AppSpace.xs + 2),
            Flexible(child: Text(ownerName, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft))),
          ],
        ),
        const SizedBox(height: AppSpace.sm),
        Wrap(
          spacing: AppSpace.xs + 2,
          runSpacing: AppSpace.xs + 2,
          children: [
            for (final reason in item.reasons)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm, vertical: AppSpace.xs - 1),
                decoration: BoxDecoration(color: AppColors.recordedBackground, borderRadius: BorderRadius.circular(AppRadius.control - 2)),
                child: Text(
                  inclusionReasonLabel(reason),
                  style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.recordedText),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

/// Totals of the period by status at the cut, and how many elements have no status at the cut. No person is ranked,
/// scored or compared: these are counts of activities. The line above the figures says that they are the status AT THE
/// CUT, so they are not read as the current one.
class SupervisionTotals extends StatelessWidget {
  const SupervisionTotals({super.key, required this.page});

  final SupervisionPage page;

  static const _looks = {
    ActivityStatus.pending: (Icons.schedule, AppColors.pendingBackground, AppColors.pendingText),
    ActivityStatus.inProgress: (Icons.trending_up, AppColors.progressBackground, AppColors.progressText),
    ActivityStatus.blocked: (Icons.block, AppColors.blockedBackground, AppColors.blockedText),
    ActivityStatus.completed: (Icons.check_circle_outline, AppColors.doneBackground, AppColors.doneText),
  };

  @override
  Widget build(BuildContext context) {
    final cards = [
      for (final status in ActivityStatus.values)
        StatCard(
          key: Key('total-${status.name}'),
          label: statusLabel(status),
          value: page.totals[status] ?? 0,
          caption: 'Estado al corte',
          showCaption: false,
          icon: _looks[status]!.$1,
          iconBackground: _looks[status]!.$2,
          iconColor: _looks[status]!.$3,
          compact: true,
        ),
    ];
    return Column(
      key: const Key('supervision-totals'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: AppSpace.sm),
          child: Text(
            'Actividades por estado al corte',
            key: Key('totals-scope'),
            style: TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w600, color: AppColors.textSoft),
          ),
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            // Four in a row when they fit, two and two otherwise. The cards of a row are as tall as the tallest of them.
            final columns = constraints.maxWidth >= 520 ? 4 : 2;
            final rows = <Widget>[];
            for (var start = 0; start < cards.length; start += columns) {
              final chunk = cards.sublist(start, (start + columns).clamp(0, cards.length));
              if (rows.isNotEmpty) rows.add(const SizedBox(height: AppSpace.sm + 2));
              rows.add(
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (var i = 0; i < chunk.length; i++) ...[
                        if (i > 0) const SizedBox(width: AppSpace.sm + 2),
                        Expanded(child: chunk[i]),
                      ],
                    ],
                  ),
                ),
              );
            }
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: rows);
          },
        ),
        const SizedBox(height: AppSpace.md),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 2),
              child: ExcludeSemantics(child: Icon(Icons.info_outline, size: 14, color: AppColors.textSoft)),
            ),
            const SizedBox(width: AppSpace.sm),
            Expanded(
              child: Text(
                'Sin estado al corte: ${page.withoutStatus.minimalReferences} referencias mínimas y ${page.withoutStatus.activities} actividades. '
                'No están en los totales de arriba.',
                key: const Key('without-status'),
                style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
