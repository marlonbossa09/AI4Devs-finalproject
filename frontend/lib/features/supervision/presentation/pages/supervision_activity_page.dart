import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
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
    final mobile = ScreenSize.ofContext(context).isMobile;
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
      body = const EmptyState('Elige una actividad en la supervisión para ver su historial.', key: Key('supervision-activity-none'));
    } else {
      final result = ref.watch(activityHistoryProvider(target.id));
      if (result.isLoading) {
        body = const Padding(
          key: Key('supervision-activity-loading'),
          padding: EdgeInsets.all(28),
          child: Center(child: CircularProgressIndicator()),
        );
      } else if (result.hasError) {
        final error = result.error;
        body = ErrorBox(
          message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
          onRetry: () => ref.invalidate(activityHistoryProvider(target.id)),
        );
      } else {
        final history = result.value;
        body = switch (history) {
          null => const EmptyState('Esta actividad no está disponible.', key: Key('supervision-activity-unavailable')),
          ActivityHistoryReference(:final reference) => MinimalReferenceBlock(reference: reference, ownerName: nameOf(reference.ownerId)),
          ActivityHistoryDetail() => _Detail(history: history, nameOf: nameOf),
        };
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(padding: const EdgeInsets.only(bottom: 10), child: back),
        const PageHeader(
          eyebrow: 'Supervisión',
          title: 'Historial de la actividad',
          subtitle: 'Lo que puedes consultar de esta actividad de tu equipo, solo en lectura.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 790),
            child: AppCard(padding: EdgeInsets.all(mobile ? 18 : 24), child: body),
          ),
        ),
      ],
    );
  }
}

class _Detail extends ConsumerWidget {
  const _Detail({required this.history, required this.nameOf});

  final ActivityHistoryDetail history;
  final String Function(String) nameOf;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activity = history.activity;
    return Column(
      key: const Key('supervision-activity'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (activity.isNeutral)
          const Row(
            children: [
              Icon(Icons.link, size: 18, color: AppColors.textSoft),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  neutralActivityLabel,
                  key: Key('neutral-label'),
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppColors.textSoft),
                ),
              ),
            ],
          )
        else
          Wrap(
            spacing: 10,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(activity.title!, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
              if (activity.origin != null) OriginTag(origin: activity.origin!),
              if (activity.isMarked) const MarkedTag(),
            ],
          ),
        const SizedBox(height: 6),
        Text(nameOf(activity.ownerId), style: const TextStyle(fontSize: 12.5, color: AppColors.textSoft)),
        if (history.currentStatus != null) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const Text('Estado actual', key: Key('history-current-status-label'), style: TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
              StatusPill(label: statusLabel(history.currentStatus!), kind: pillKind(history.currentStatus!)),
            ],
          ),
        ],
        if (activity.isMarked) ...[
          const SizedBox(height: 6),
          Text('Motivo de la marca: ${activity.markReason}', style: const TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
        ],
        const SizedBox(height: 6),
        const Text(
          'Solo lectura: esta actividad no se puede modificar desde aquí.',
          key: Key('supervision-readonly-note'),
          style: TextStyle(fontSize: 11, color: AppColors.textFaint),
        ),
        const SizedBox(height: 18),
        const _Caption('Planificaciones'),
        const SizedBox(height: 6),
        if (history.plannings.isEmpty)
          const Text('No hay planificaciones que puedas consultar.', key: Key('supervision-no-plannings'), style: TextStyle(fontSize: 12.5, color: AppColors.textFaint))
        else
          for (final p in history.plannings)
            _Entry(
              icon: Icons.event_note_outlined,
              label: p.type == PlanningType.original ? 'Planificada' : 'Continuación planificada',
              date: p.date,
              text: p.description,
            ),
        const SizedBox(height: 18),
        const _Caption('Avances, en orden histórico'),
        const SizedBox(height: 6),
        if (history.progress.isEmpty)
          const Text('No hay avances que puedas consultar.', key: Key('supervision-no-progress'), style: TextStyle(fontSize: 12.5, color: AppColors.textFaint))
        else
          for (final a in history.progress)
            _Entry(
              icon: Icons.check_circle_outline,
              label: 'Avance',
              date: a.date,
              text: a.description,
              status: a.status,
              blockReason: a.blockReason,
            ),
        if (!activity.isNeutral) ...[
          const SizedBox(height: 18),
          Align(
            alignment: Alignment.centerLeft,
            child: SecondaryButton(
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
          ),
        ],
      ],
    );
  }
}

class _Caption extends StatelessWidget {
  const _Caption(this.text);

  final String text;

  @override
  Widget build(BuildContext context) =>
      Text(text, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: AppColors.textLabel));
}

class _Entry extends StatelessWidget {
  const _Entry({required this.icon, required this.label, required this.date, required this.text, this.status, this.blockReason});

  final IconData icon;
  final String label;
  final DateTime date;
  final String text;
  final ActivityStatus? status;
  final String? blockReason;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFAFBFD),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 15, color: AppColors.textSoft),
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
                    Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppColors.textSoft)),
                    Text(formatShortDate(date), style: const TextStyle(fontSize: 11, color: AppColors.textFaint)),
                    if (status != null) StatusPill(label: statusLabel(status!), kind: pillKind(status!)),
                  ],
                ),
                if (text.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 3), child: Text(text, style: const TextStyle(fontSize: 12.5, height: 1.45))),
                if (blockReason != null && blockReason!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Text('Motivo del bloqueo: $blockReason', style: const TextStyle(fontSize: 11.5, color: AppColors.textSoft)),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
