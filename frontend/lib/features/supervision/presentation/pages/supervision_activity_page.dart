import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../../logbook/domain/entities/audit_entities.dart';
import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../../logbook/presentation/providers/navigation.dart';
import '../../../logbook/presentation/widgets/activity_tile.dart' show pillKind, statusLabel;
import '../../../logbook/presentation/widgets/marked_tag.dart';
import '../../../logbook/presentation/widgets/origin_tag.dart';
import '../../../team/domain/entities/team_entities.dart';
import '../../../team/presentation/providers/team_data.dart';
import '../../domain/entities/supervision_entities.dart';
import '../providers/supervision_data.dart';
import '../providers/supervision_navigation.dart';
import '../widgets/supervision_item_tile.dart';

/// The history of ONE activity of the team (M4-04), READ-ONLY: there is no control to change, close, reopen, mark or
/// correct anything. It shows exactly what the server authorizes:
///
/// - `full` activity: its title, tags, the authorized plannings and the authorized progress in historical order, each
///   with its own description and block reason, and a link to its audit (M3-07).
/// - `neutral` activity: only "Actividad en continuidad" with the authorized plannings and progress. No audit link: the
///   audit of that record is not the supervisor's, and the page never tries other endpoints to learn a title or a reason.
/// - minimal reference: only the reference.
///
/// Nothing absent is invented: no title, status or date that the server did not send.
class SupervisionActivityPage extends ConsumerWidget {
  const SupervisionActivityPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pad = ScreenSize.ofContext(context).isMobile ? AppSpace.lg : AppSpace.xl;
    final target = ref.watch(supervisionActivityTargetProvider);
    final myId = ref.watch(authProvider).value?.user.id;
    final members = ref.watch(teamMembersProvider).value ?? const <TeamMember>[];

    String nameOf(String id) {
      if (id == myId) return 'Tú';
      for (final member in members) {
        if (member.id == id) return member.name;
      }
      return 'Persona que ya no está en tu equipo';
    }

    final back = LinkButton(
      key: const Key('supervision-activity-back'),
      label: '← Volver a la supervisión',
      onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.supervision),
    );

    Widget body;
    if (target == null) {
      body = AppCard(
        padding: EdgeInsets.all(pad),
        child: const EmptyState('Elige una actividad en la supervisión para ver su historial.', key: Key('supervision-activity-none')),
      );
    } else {
      final result = ref.watch(activityHistoryProvider(target.id));
      if (result.isLoading) {
        body = AppCard(
          child: Padding(
            key: const Key('supervision-activity-loading'),
            padding: const EdgeInsets.all(AppSpace.xxl + AppSpace.sm),
            child: const Center(child: CircularProgressIndicator(semanticsLabel: 'Cargando la actividad')),
          ),
        );
      } else if (result.hasError) {
        final error = result.error;
        body = AppCard(
          padding: EdgeInsets.symmetric(horizontal: pad),
          child: ErrorBox(
            message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
            onRetry: () => ref.invalidate(activityHistoryProvider(target.id)),
          ),
        );
      } else {
        final history = result.value;
        body = switch (history) {
          null => AppCard(
            padding: EdgeInsets.all(pad),
            child: const EmptyState('Esta actividad no está disponible.', key: Key('supervision-activity-unavailable')),
          ),
          ActivityHistoryReference(:final reference) => AppCard(
            padding: EdgeInsets.all(pad),
            child: MinimalReferenceBlock(reference: reference, ownerName: nameOf(reference.ownerId)),
          ),
          ActivityHistoryDetail() => _Detail(history: history, nameOf: nameOf, pad: pad),
        };
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(padding: const EdgeInsets.only(bottom: AppSpace.sm), child: back),
        const PageHeader(
          eyebrow: 'Supervisión',
          title: 'Historial de la actividad',
          subtitle: 'Lo que puedes consultar de esta actividad de tu equipo, solo en lectura.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 920), child: body),
        ),
      ],
    );
  }
}

class _Detail extends ConsumerWidget {
  const _Detail({required this.history, required this.nameOf, required this.pad});

  final ActivityHistoryDetail history;
  final String Function(String) nameOf;
  final double pad;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activity = history.activity;
    return Column(
      key: const Key('supervision-activity'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppCard(
          padding: EdgeInsets.all(pad),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (activity.isNeutral)
                Row(
                  children: [
                    const ExcludeSemantics(child: Icon(Icons.link, size: 18, color: AppColors.textSoft)),
                    const SizedBox(width: AppSpace.sm),
                    Expanded(
                      child: Semantics(
                        header: true,
                        child: Text(
                          neutralActivityLabel,
                          key: const Key('neutral-label'),
                          style: context.heading(AppType.cardTitle, color: AppColors.textSoft),
                        ),
                      ),
                    ),
                  ],
                )
              else
                Wrap(
                  spacing: AppSpace.sm,
                  runSpacing: AppSpace.xs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Semantics(header: true, child: Text(activity.title!, style: context.heading(AppType.cardTitle))),
                    if (activity.origin != null) OriginTag(origin: activity.origin!),
                    if (activity.isMarked) const MarkedTag(),
                  ],
                ),
              const SizedBox(height: AppSpace.xs + 2),
              Row(
                children: [
                  const ExcludeSemantics(child: Icon(Icons.person_outline, size: 14, color: AppColors.textSoft)),
                  const SizedBox(width: AppSpace.xs + 2),
                  Flexible(child: Text(nameOf(activity.ownerId), style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft))),
                ],
              ),
              if (history.currentStatus != null) ...[
                const SizedBox(height: AppSpace.md),
                StatusLine(
                  label: 'Estado actual',
                  icon: Icons.update,
                  status: history.currentStatus,
                  labelKey: const Key('history-current-status-label'),
                ),
              ],
              if (activity.isMarked) ...[
                const SizedBox(height: AppSpace.sm),
                Text(
                  'Motivo de la marca: ${activity.markReason}',
                  style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
                ),
              ],
              const SizedBox(height: AppSpace.sm),
              const Row(
                children: [
                  ExcludeSemantics(child: Icon(Icons.lock_outline, size: 14, color: AppColors.textSoft)),
                  SizedBox(width: AppSpace.xs + 2),
                  Expanded(
                    child: Text(
                      'Solo lectura: esta actividad no se puede modificar desde aquí.',
                      key: Key('supervision-readonly-note'),
                      style: TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
                    ),
                  ),
                ],
              ),
              if (!activity.isNeutral) ...[
                const SizedBox(height: AppSpace.md),
                SecondaryButton(
                  key: const Key('supervision-audit'),
                  label: 'Ver auditoría de la actividad',
                  onPressed: () {
                    ref.read(auditTargetProvider.notifier).select(
                      type: AuditObjectType.activity,
                      objectId: activity.id,
                      title: activity.title!,
                      back: AppPage.supervisionActivity,
                    );
                    ref.read(currentPageProvider.notifier).go(AppPage.audit);
                  },
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        AppCard(
          padding: EdgeInsets.all(pad),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const PanelHeader(title: 'Planificaciones', bottom: AppSpace.xs),
              if (history.plannings.isEmpty)
                const _None('No hay planificaciones que puedas consultar.', key: Key('supervision-no-plannings'))
              else
                for (var i = 0; i < history.plannings.length; i++)
                  _Entry(
                    first: i == 0,
                    icon: Icons.event_note_outlined,
                    label: history.plannings[i].type == PlanningType.original ? 'Planificada' : 'Continuación planificada',
                    date: history.plannings[i].date,
                    text: history.plannings[i].description,
                  ),
              const SizedBox(height: AppSpace.xl),
              const PanelHeader(title: 'Avances, en orden histórico', bottom: AppSpace.xs),
              if (history.progress.isEmpty)
                const _None('No hay avances que puedas consultar.', key: Key('supervision-no-progress'))
              else
                for (var i = 0; i < history.progress.length; i++)
                  _Entry(
                    first: i == 0,
                    icon: Icons.check_circle_outline,
                    label: 'Avance',
                    date: history.progress[i].date,
                    text: history.progress[i].description,
                    status: history.progress[i].status,
                    blockReason: history.progress[i].blockReason,
                  ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Said when a section has nothing the supervisor may read.
class _None extends StatelessWidget {
  const _None(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: AppSpace.sm),
    child: Text(text, style: const TextStyle(fontSize: AppType.body, color: AppColors.textSoft)),
  );
}

/// One planning or progress entry, as a dense row of a list (it draws its own top divider unless it is the [first]).
class _Entry extends StatelessWidget {
  const _Entry({
    required this.first,
    required this.icon,
    required this.label,
    required this.date,
    required this.text,
    this.status,
    this.blockReason,
  });

  final bool first;
  final IconData icon;
  final String label;
  final DateTime date;
  final String text;
  final ActivityStatus? status;
  final String? blockReason;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
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
                    Text(formatShortDate(date), style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
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
