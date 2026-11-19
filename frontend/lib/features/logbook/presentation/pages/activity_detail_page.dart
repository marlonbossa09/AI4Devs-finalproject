import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/audit_entities.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/continuation_rules.dart';
import '../../domain/rules/correction_rules.dart';
import '../../domain/rules/mark_rules.dart';
import '../../domain/rules/reactivation_rules.dart';
import '../providers/activity_detail.dart';
import '../providers/navigation.dart';
import '../widgets/activity_tile.dart';
import '../widgets/continuation_tag.dart';
import '../widgets/form_parts.dart';
import '../widgets/mark_actions.dart';
import '../widgets/marked_tag.dart';
import '../widgets/origin_tag.dart';
import '../widgets/reactivation_tag.dart';

/// One activity with everything recorded about it (M2-07). What was PLANNED and what was DONE are
/// shown in separate blocks, so a planning is never mistaken for a progress entry (CA-40).
///
/// Reading order: the title with its main action, the current status and facts of the activity, what was planned, and what
/// was done. On a wide screen the status and its facts are a column beside the planning and the history; on a tablet or a
/// phone they come first and the rest follows.
class ActivityDetailPage extends ConsumerWidget {
  const ActivityDetailPage({super.key});

  String _backLabel(AppPage page) => switch (page) {
    AppPage.logbook => 'Mi bitácora',
    AppPage.dashboard => 'Panel principal',
    _ => 'Mis actividades',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final opened = ref.watch(activityNavProvider);
    if (opened == null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AppCard(
            padding: EdgeInsets.all(AppSpace.lg),
            child: EmptyState('No hay una actividad abierta.', key: Key('detail-none')),
          ),
          const SizedBox(height: AppSpace.sm),
          LinkButton(
            key: const Key('detail-back'),
            label: '← Mis actividades',
            onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.activities),
          ),
        ],
      );
    }
    final view = ref.watch(activityDetailProvider(opened.id));

    Widget body;
    // Only the FIRST load replaces the page: a reload keeps showing what it had (and keeps its dialogs alive)
    if (view.isLoading && !view.hasValue) {
      body = const AppCard(child: KeyedSubtree(key: Key('detail-loading'), child: LoadingBlock()));
    } else if (view.hasError && !view.hasValue) {
      final error = view.error;
      body = AppCard(
        padding: const EdgeInsets.all(AppSpace.lg),
        child: ErrorBox(
          message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
          onRetry: () => ref.invalidate(activityDetailProvider(opened.id)),
        ),
      );
    } else {
      body = _DetailBody(
        detail: view.requireValue,
        onRegisterProgress: () {
          final activity = view.requireValue.activity;
          ref.read(progressTargetProvider.notifier).select(activity.summary, back: AppPage.activityDetail);
          ref.read(currentPageProvider.notifier).go(AppPage.progress);
        },
        onPlanContinuation: () {
          final activity = view.requireValue.activity;
          ref.read(continuationTargetProvider.notifier).select(activity.summary, back: AppPage.activityDetail);
          ref.read(currentPageProvider.notifier).go(AppPage.continuation);
        },
        onReactivate: () {
          final activity = view.requireValue.activity;
          ref.read(reactivationTargetProvider.notifier).select(activity.summary, back: AppPage.activityDetail);
          ref.read(currentPageProvider.notifier).go(AppPage.reactivation);
        },
        onCorrect: (entry) {
          ref.read(correctionTargetProvider.notifier).select(
            activityId: view.requireValue.activity.id,
            progressId: entry.id,
            back: AppPage.activityDetail,
          );
          ref.read(currentPageProvider.notifier).go(AppPage.correction);
        },
        onAudit: () {
          final activity = view.requireValue.activity;
          ref.read(auditTargetProvider.notifier).select(
            type: AuditObjectType.activity,
            objectId: activity.id,
            title: activity.title,
            back: AppPage.activityDetail,
          );
          ref.read(currentPageProvider.notifier).go(AppPage.audit);
        },
        onAuditProgress: (entry) {
          ref.read(auditTargetProvider.notifier).select(
            type: AuditObjectType.progress,
            objectId: entry.id,
            title: 'Avance del ${formatShortDate(entry.date)}: ${entry.description}',
            back: AppPage.activityDetail,
          );
          ref.read(currentPageProvider.notifier).go(AppPage.audit);
        },
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: AppSpace.xs),
          child: LinkButton(
            key: const Key('detail-back'),
            label: '← ${_backLabel(opened.back)}',
            onPressed: () => ref.read(currentPageProvider.notifier).go(opened.back),
          ),
        ),
        body,
      ],
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({
    required this.detail,
    required this.onRegisterProgress,
    required this.onPlanContinuation,
    required this.onReactivate,
    required this.onCorrect,
    required this.onAudit,
    required this.onAuditProgress,
  });

  final ActivityDetail detail;
  final VoidCallback onRegisterProgress;
  final VoidCallback onPlanContinuation;
  final VoidCallback onReactivate;
  final ValueChanged<Progress> onCorrect;

  /// Opens the audit of the activity, or of one of its progress entries (M3-07).
  final VoidCallback onAudit;
  final ValueChanged<Progress> onAuditProgress;

  @override
  Widget build(BuildContext context) {
    final activity = detail.activity;
    final size = ScreenSize.ofContext(context);
    final reactivable = canReactivate(status: detail.status, marked: activity.marked);
    // ONE main action: reactivating a Completada activity is what the person came for; otherwise it is registering progress.
    final register = reactivable
        ? SecondaryButton(
            key: const Key('detail-register-progress'),
            label: 'Registrar avance',
            onPressed: activity.marked ? null : onRegisterProgress,
          )
        : PrimaryButton(
            key: const Key('detail-register-progress'),
            label: 'Registrar avance',
            icon: Icons.add,
            onPressed: activity.marked ? null : onRegisterProgress,
          );
    final status = _StatusCard(detail: detail, onAudit: onAudit);
    final planning = _PlanningCard(detail: detail);
    final history = _HistoryCard(
      progress: detail.progress,
      // The entries of a marked activity are not corrected until the mark is reverted (D-05)
      onCorrect: canCorrect(detail.activity) ? onCorrect : null,
      onAudit: onAuditProgress,
      marked: detail.activity.marked,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          eyebrow: 'Detalle de actividad',
          title: activity.title,
          subtitle: 'Lo que se planificó, lo que se hizo y el estado en que está hoy.',
          action: Wrap(
            spacing: AppSpace.sm,
            runSpacing: AppSpace.sm,
            alignment: size.isMobile ? WrapAlignment.start : WrapAlignment.end,
            children: [
              if (canPlanContinuation(status: detail.status, marked: activity.marked))
                SecondaryButton(
                  key: const Key('detail-plan-continuation'),
                  label: 'Planificar continuación',
                  onPressed: onPlanContinuation,
                ),
              if (reactivable)
                PrimaryButton(
                  key: const Key('detail-reactivate'),
                  label: 'Reactivar actividad',
                  icon: Icons.replay,
                  onPressed: onReactivate,
                ),
              register,
            ],
          ),
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            if (size.isDesktop) {
              final side = (constraints.maxWidth * 0.34).clamp(320.0, 400.0);
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [planning, const SizedBox(height: AppSpace.lg), history],
                    ),
                  ),
                  const SizedBox(width: AppSpace.xl),
                  SizedBox(width: side, child: status),
                ],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [status, const SizedBox(height: AppSpace.lg), planning, const SizedBox(height: AppSpace.lg), history],
            );
          },
        ),
      ],
    );
  }
}

/// A card of the detail: its padding follows the screen.
EdgeInsets _cardPadding(BuildContext context) => EdgeInsets.all(FormCard.padding(context));

/// The current status, the facts of the activity (how it started, its origin day, when it was created), the mark of error when
/// it has one, and what can be done about the activity itself: its audit and, if it applies, marking or reverting the mark.
class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.detail, required this.onAudit});

  final ActivityDetail detail;

  /// Opens the audit of the activity (M3-07): who changed it, when and how. It is not the work history below.
  final VoidCallback onAudit;

  @override
  Widget build(BuildContext context) {
    final activity = detail.activity;
    final origin = activity.origin == ActivityOrigin.planned ? 'Actividad planificada' : 'Actividad no planificada';
    final markable = canRevertMark(activity) || canMarkAsError(activity: activity, progress: detail.progress);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: _cardPadding(context),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                PanelHeader(
                  title: 'Estado actual',
                  subtitle: 'El del último avance de ejecución; Pendiente si todavía no tiene ninguno.',
                  trailing: KeyedSubtree(
                    key: const Key('detail-status'),
                    child: StatusPill(label: statusLabel(detail.status), kind: pillKind(detail.status)),
                  ),
                  bottom: AppSpace.md,
                ),
                _Fact(
                  'Tipo',
                  activity.origin == ActivityOrigin.unplanned
                      ? KeyedSubtree(key: const Key('detail-origin-tag'), child: OriginTag(origin: activity.origin))
                      : Text(origin, style: _factStyle),
                  first: true,
                ),
                _Fact(
                  'Jornada de origen',
                  Text(formatShortDate(activity.date), key: const Key('detail-origin-date'), style: _factStyle),
                ),
                _Fact('Creada el', Text(formatDateTime(activity.createdAt), style: _factStyle)),
                if (activity.marked) ...[
                  const SizedBox(height: AppSpace.md),
                  Container(
                    key: const Key('detail-marked'),
                    width: double.infinity,
                    padding: const EdgeInsets.all(AppSpace.md),
                    decoration: BoxDecoration(
                      color: MarkedColors.background,
                      borderRadius: BorderRadius.circular(AppRadius.control + 2),
                      border: Border.all(color: MarkedColors.border),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const KeyedSubtree(key: Key('detail-marked-tag'), child: MarkedTag()),
                        const SizedBox(height: AppSpace.sm),
                        const Text(
                          'Esta actividad se marcó como registrada por error: no aparece en tus vistas ni recuentos y ya '
                          'no admite avances. Su historial se conserva y puedes revertir la marca.',
                          style: TextStyle(fontSize: AppType.caption, height: 1.5, color: MarkedColors.foreground),
                        ),
                        if (activity.markReason != null && activity.markReason!.isNotEmpty) ...[
                          const SizedBox(height: AppSpace.xs),
                          Text(
                            'Motivo: ${activity.markReason}',
                            key: const Key('detail-marked-reason'),
                            style: const TextStyle(
                              fontSize: AppType.caption,
                              height: 1.5,
                              fontWeight: FontWeight.w700,
                              color: MarkedColors.foreground,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          Container(
            width: double.infinity,
            padding: EdgeInsets.symmetric(horizontal: FormCard.padding(context) - AppSpace.sm, vertical: AppSpace.sm),
            decoration: const BoxDecoration(
              color: AppColors.panelFooter,
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: AppSpace.sm,
              runSpacing: AppSpace.xs,
              children: [
                LinkButton(key: const Key('detail-audit'), label: 'Ver historial de auditoría', onPressed: onAudit),
                if (markable) ActivityMarkActions(activity: activity, progress: detail.progress),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

const _factStyle = TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w700, color: AppColors.ink);

/// One fact of the activity: its label at the start and its value at the end of the line.
class _Fact extends StatelessWidget {
  const _Fact(this.label, this.value, {this.first = false});

  final String label;
  final Widget value;
  final bool first;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.sm),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(label, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Align(
              alignment: Alignment.centerRight,
              child: DefaultTextStyle.merge(textAlign: TextAlign.end, child: value),
            ),
          ),
        ],
      ),
    );
  }
}

/// WHAT WAS FORESEEN. Not a progress entry: it never changes the status.
class _PlanningCard extends StatelessWidget {
  const _PlanningCard({required this.detail});

  final ActivityDetail detail;

  @override
  Widget build(BuildContext context) {
    final original = detail.originalPlanning;

    Widget block(
      Key key,
      String title,
      String date,
      String description, {
      String? registered,
      bool continuation = false,
    }) {
      final accent = continuation ? ContinuationColors.foreground : AppColors.recordedText;
      return Container(
        key: key,
        width: double.infinity,
        margin: const EdgeInsets.only(top: AppSpace.md),
        padding: const EdgeInsets.all(AppSpace.md),
        decoration: BoxDecoration(
          color: continuation ? ContinuationColors.background.withValues(alpha: 0.55) : AppColors.background,
          borderRadius: BorderRadius.circular(AppRadius.control + 2),
          border: Border.all(color: continuation ? ContinuationColors.border : AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (continuation) ...[const ContinuationTag(), const SizedBox(height: AppSpace.sm)],
            Wrap(
              spacing: AppSpace.md,
              runSpacing: AppSpace.xs,
              children: [
                Text(title, style: TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w800, color: accent)),
                Text(date, style: TextStyle(fontSize: AppType.caption, color: accent)),
                if (registered != null)
                  Text('Registrada $registered', style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
              ],
            ),
            const SizedBox(height: AppSpace.xs),
            Text(
              description.isEmpty ? 'Sin descripción' : description,
              style: const TextStyle(fontSize: AppType.body, height: 1.5, color: AppColors.textBody),
            ),
          ],
        ),
      );
    }

    return AppCard(
      padding: _cardPadding(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const TaggedHeader(
            title: 'Lo planificado',
            subtitle: 'Lo que se tenía previsto. No es un avance y no cambia el estado de la actividad.',
            tag: KindTag(
              'Planificación',
              icon: Icons.event_note_outlined,
              color: AppColors.recordedText,
              background: AppColors.recordedBackground,
            ),
            bottom: 0,
          ),
          if (original != null)
            block(
              const Key('detail-planning-original'),
              'Planificación original',
              formatShortDate(original.date),
              original.description,
              registered: formatDateTime(original.createdAt),
            )
          else
            Padding(
              key: const Key('detail-no-planning'),
              padding: const EdgeInsets.only(top: AppSpace.md),
              child: const Text(
                'Esta actividad no se planificó: se registró directamente como ejecución.',
                style: TextStyle(fontSize: AppType.body, color: AppColors.textSoft),
              ),
            ),
          for (final next in detail.plannedContinuations)
            block(
              Key('detail-planning-${next.id}'),
              'Continuación planificada',
              formatShortDate(next.date),
              next.description,
              registered: formatDateTime(next.createdAt),
              continuation: true,
            ),
        ],
      ),
    );
  }
}

/// WHAT WAS DONE. Each entry keeps the status the activity had when it was recorded.
class _HistoryCard extends StatelessWidget {
  const _HistoryCard({
    required this.progress,
    required this.onCorrect,
    required this.onAudit,
    required this.marked,
  });

  final List<Progress> progress;
  final ValueChanged<Progress>? onCorrect;
  final ValueChanged<Progress> onAudit;
  final bool marked;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: _cardPadding(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const TaggedHeader(
            title: 'Historial de avances',
            subtitle: 'Lo que realmente se hizo, ordenado por fecha laboral. Cada avance conserva el estado que tenía entonces.',
            tag: KindTag(
              'Ejecución',
              icon: Icons.trending_up,
              color: AppColors.progressText,
              background: AppColors.progressBackground,
            ),
            bottom: AppSpace.sm,
          ),
          if (marked)
            const Padding(
              padding: EdgeInsets.only(bottom: AppSpace.sm),
              child: FormHint(
                'Los avances de una actividad marcada como registrada por error no se corrigen: revierte antes la marca.',
                textKey: Key('detail-correct-blocked'),
              ),
            ),
          if (progress.isEmpty)
            const EmptyState('Todavía no hay avances registrados.', key: Key('detail-no-progress'))
          else
            for (var i = 0; i < progress.length; i++)
              _ProgressEntry(
                key: Key('detail-progress-${progress[i].id}'),
                entry: progress[i],
                first: i == 0,
                onCorrect: onCorrect == null ? null : () => onCorrect!(progress[i]),
                onAudit: () => onAudit(progress[i]),
              ),
        ],
      ),
    );
  }
}

class _ProgressEntry extends StatelessWidget {
  const _ProgressEntry({super.key, required this.entry, required this.first, required this.onAudit, this.onCorrect});

  final Progress entry;
  final bool first;

  /// Opens the audit of THIS entry (M3-07): the corrections and changes made to it, not the work history.
  final VoidCallback onAudit;

  /// Opens the correction form (M3-03). Null when the entry cannot be corrected.
  final VoidCallback? onCorrect;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final reason = entry.blockReason;
    final date = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Fecha laboral', style: TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
        Text(
          formatShortDate(entry.date),
          key: Key('detail-progress-date-${entry.id}'),
          style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink),
        ),
        const SizedBox(height: AppSpace.xs),
        Text(
          'Registrado ${formatDateTime(entry.createdAt)}',
          style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
        ),
        // A corrected entry says so and when; an entry never corrected shows nothing (CA-62)
        if (entry.corrected)
          Text(
            'Corregido ${formatDateTime(entry.modifiedAt!)}',
            key: Key('detail-corrected-${entry.id}'),
            style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.textSecondary),
          ),
      ],
    );
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: AppSpace.sm,
          runSpacing: AppSpace.xs,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            KeyedSubtree(
              key: Key('detail-progress-status-${entry.id}'),
              child: StatusPill(label: statusLabel(entry.status), kind: pillKind(entry.status)),
            ),
            if (entry.isReactivation)
              KeyedSubtree(key: Key('detail-reactivation-${entry.id}'), child: const ReactivationTag()),
          ],
        ),
        const SizedBox(height: AppSpace.sm),
        Text(entry.description, style: const TextStyle(fontSize: AppType.body, height: 1.5, color: AppColors.textBody)),
        if (reason != null && reason.isNotEmpty) ...[
          const SizedBox(height: AppSpace.xs),
          Text(
            'Motivo del bloqueo: $reason',
            style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.blockedText),
          ),
        ],
        const SizedBox(height: AppSpace.xs),
        Wrap(
          spacing: AppSpace.sm,
          children: [
            if (onCorrect != null)
              LinkButton(key: Key('detail-correct-${entry.id}'), label: 'Corregir', onPressed: onCorrect),
            LinkButton(key: Key('detail-audit-${entry.id}'), label: 'Ver auditoría', onPressed: onAudit),
          ],
        ),
      ],
    );
    return Container(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
      child: mobile
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [date, const SizedBox(height: AppSpace.md), content],
            )
          : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [SizedBox(width: 156, child: date), const SizedBox(width: AppSpace.lg), Expanded(child: content)],
            ),
    );
  }
}
