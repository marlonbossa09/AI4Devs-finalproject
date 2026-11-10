import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
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
import '../widgets/mark_actions.dart';
import '../widgets/marked_tag.dart';
import '../widgets/origin_tag.dart';
import '../widgets/reactivation_tag.dart';

/// One activity with everything recorded about it (M2-07). What was PLANNED and what was DONE are
/// shown in separate blocks, so a planning is never mistaken for a progress entry (CA-40).
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
          const EmptyState('No hay una actividad abierta.', key: Key('detail-none')),
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
      body = const Padding(
        key: Key('detail-loading'),
        padding: EdgeInsets.all(40),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (view.hasError && !view.hasValue) {
      final error = view.error;
      body = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
        onRetry: () => ref.invalidate(activityDetailProvider(opened.id)),
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
          padding: const EdgeInsets.only(bottom: 10),
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          eyebrow: 'Detalle de actividad',
          title: activity.title,
          subtitle: 'Lo que se planificó, lo que se hizo y el estado en que está hoy.',
          action: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              if (canPlanContinuation(status: detail.status, marked: activity.marked))
                SecondaryButton(
                  key: const Key('detail-plan-continuation'),
                  label: 'Planificar continuación',
                  onPressed: onPlanContinuation,
                ),
              if (canReactivate(status: detail.status, marked: activity.marked))
                PrimaryButton(
                  key: const Key('detail-reactivate'),
                  label: 'Reactivar actividad',
                  icon: Icons.replay,
                  onPressed: onReactivate,
                ),
              PrimaryButton(
                key: const Key('detail-register-progress'),
                label: 'Registrar avance',
                icon: Icons.add,
                onPressed: activity.marked ? null : onRegisterProgress,
              ),
              if (canRevertMark(activity) || canMarkAsError(activity: activity, progress: detail.progress))
                ActivityMarkActions(activity: activity, progress: detail.progress),
            ],
          ),
        ),
        _StatusCard(detail: detail, onAudit: onAudit),
        const SizedBox(height: 18),
        _PlanningCard(detail: detail),
        const SizedBox(height: 18),
        _HistoryCard(
          progress: detail.progress,
          // The entries of a marked activity are not corrected until the mark is reverted (D-05)
          onCorrect: canCorrect(detail.activity) ? onCorrect : null,
          onAudit: onAuditProgress,
          marked: detail.activity.marked,
        ),
      ],
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.detail, required this.onAudit});

  final ActivityDetail detail;

  /// Opens the audit of the activity (M3-07): who changed it, when and how. It is not the work history below.
  final VoidCallback onAudit;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final activity = detail.activity;
    final origin = activity.origin == ActivityOrigin.planned ? 'Actividad planificada' : 'Actividad no planificada';
    Widget fact(String label, String value, {Key? key}) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textFaint)),
        const SizedBox(height: 3),
        Text(value, key: key, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
      ],
    );
    return AppCard(
      padding: EdgeInsets.all(mobile ? 18 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Estado actual', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
              const SizedBox(width: 12),
              KeyedSubtree(
                key: const Key('detail-status'),
                child: StatusPill(label: statusLabel(detail.status), kind: pillKind(detail.status)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'El del último avance de ejecución; Pendiente si todavía no tiene ninguno.',
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 34,
            runSpacing: 12,
            children: [
              if (activity.origin == ActivityOrigin.unplanned)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Tipo', style: TextStyle(fontSize: 10, color: AppColors.textFaint)),
                    const SizedBox(height: 3),
                    KeyedSubtree(key: const Key('detail-origin-tag'), child: OriginTag(origin: activity.origin)),
                  ],
                )
              else
                fact('Tipo', origin),
              fact('Jornada de origen', formatShortDate(activity.date), key: const Key('detail-origin-date')),
              fact('Creada el', formatDateTime(activity.createdAt)),
            ],
          ),
          if (activity.marked) ...[
            const SizedBox(height: 16),
            Container(
              key: const Key('detail-marked'),
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: MarkedColors.background,
                borderRadius: BorderRadius.circular(11),
                border: Border.all(color: MarkedColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const KeyedSubtree(key: Key('detail-marked-tag'), child: MarkedTag()),
                  const SizedBox(height: 8),
                  Text(
                    'Esta actividad se marcó como registrada por error: no aparece en tus vistas ni recuentos y ya '
                    'no admite avances. Su historial se conserva y puedes revertir la marca.',
                    style: const TextStyle(fontSize: 11, height: 1.6, color: MarkedColors.foreground),
                  ),
                  if (activity.markReason != null && activity.markReason!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Motivo: ${activity.markReason}',
                      key: const Key('detail-marked-reason'),
                      style: const TextStyle(fontSize: 11, height: 1.6, fontWeight: FontWeight.w700, color: MarkedColors.foreground),
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerLeft,
            child: LinkButton(
              key: const Key('detail-audit'),
              label: 'Ver historial de auditoría',
              onPressed: onAudit,
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
    final mobile = ScreenSize.ofContext(context).isMobile;
    final original = detail.originalPlanning;

    Widget block(
      Key key,
      String title,
      String date,
      String description, {
      String? registered,
      bool continuation = false,
    }) {
      final accent = continuation ? ContinuationColors.foreground : const Color(0xFF276A67);
      return Container(
        key: key,
        width: double.infinity,
        margin: const EdgeInsets.only(top: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: continuation ? ContinuationColors.background.withValues(alpha: 0.55) : const Color(0xFFF3FAF8),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: continuation ? ContinuationColors.border : const Color(0xFFDAEEE9)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (continuation) ...[const ContinuationTag(), const SizedBox(height: 8)],
            Wrap(
              spacing: 10,
              children: [
                Text(title, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: accent)),
                Text(date, style: TextStyle(fontSize: 11, color: accent)),
                if (registered != null)
                  Text('Registrada $registered', style: const TextStyle(fontSize: 10, color: AppColors.textFaint)),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              description.isEmpty ? 'Sin descripción' : description,
              style: const TextStyle(fontSize: 12, height: 1.6, color: AppColors.textBody),
            ),
          ],
        ),
      );
    }

    return AppCard(
      padding: EdgeInsets.all(mobile ? 18 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const KindTag('Planificación', icon: Icons.event_note_outlined, color: Color(0xFF276A67), background: Color(0xFFE5F7F3)),
          const SizedBox(height: 10),
          const Text('Lo planificado', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text(
            'Lo que se tenía previsto. No es un avance y no cambia el estado de la actividad.',
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
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
            Container(
              key: const Key('detail-no-planning'),
              margin: const EdgeInsets.only(top: 10),
              child: const Text(
                'Esta actividad no se planificó: se registró directamente como ejecución.',
                style: TextStyle(fontSize: 12, color: AppColors.textSoft),
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
    final mobile = ScreenSize.ofContext(context).isMobile;
    return AppCard(
      padding: EdgeInsets.all(mobile ? 18 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const KindTag('Ejecución', icon: Icons.trending_up, color: AppColors.progressText, background: AppColors.progressBackground),
          const SizedBox(height: 10),
          const Text('Historial de avances', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text(
            'Lo que realmente se hizo, ordenado por fecha laboral. Cada avance conserva el estado que tenía entonces.',
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          if (marked) ...[
            const SizedBox(height: 6),
            const Text(
              'Los avances de una actividad marcada como registrada por error no se corrigen: revierte antes la marca.',
              key: Key('detail-correct-blocked'),
              style: TextStyle(fontSize: 11, color: AppColors.textSoft),
            ),
          ],
          const SizedBox(height: 8),
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
        const Text('Fecha laboral', style: TextStyle(fontSize: 10, color: AppColors.textFaint)),
        const SizedBox(height: 2),
        Text(
          formatShortDate(entry.date),
          key: Key('detail-progress-date-${entry.id}'),
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 4),
        Text(
          'Registrado ${formatDateTime(entry.createdAt)}',
          style: const TextStyle(fontSize: 10, color: AppColors.textFaint),
        ),
        // A corrected entry says so and when; an entry never corrected shows nothing (CA-62)
        if (entry.corrected) ...[
          const SizedBox(height: 2),
          Text(
            'Corregido ${formatDateTime(entry.modifiedAt!)}',
            key: Key('detail-corrected-${entry.id}'),
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.textSoft),
          ),
        ],
      ],
    );
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
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
        const SizedBox(height: 8),
        Text(entry.description, style: const TextStyle(fontSize: 12, height: 1.6, color: AppColors.textBody)),
        if (reason != null && reason.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(
            'Motivo del bloqueo: $reason',
            style: const TextStyle(fontSize: 11, height: 1.55, color: AppColors.blockedText),
          ),
        ],
        const SizedBox(height: 4),
        Align(
          alignment: Alignment.centerLeft,
          child: Wrap(
            spacing: 14,
            children: [
              if (onCorrect != null)
                LinkButton(
                  key: Key('detail-correct-${entry.id}'),
                  label: 'Corregir',
                  onPressed: onCorrect,
                ),
              LinkButton(
                key: Key('detail-audit-${entry.id}'),
                label: 'Ver auditoría',
                onPressed: onAudit,
              ),
            ],
          ),
        ),
      ],
    );
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: first ? null : const Border(top: BorderSide(color: AppColors.divider)),
      ),
      child: mobile
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [date, const SizedBox(height: 10), content],
            )
          : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [SizedBox(width: 150, child: date), const SizedBox(width: 18), Expanded(child: content)],
            ),
    );
  }
}
