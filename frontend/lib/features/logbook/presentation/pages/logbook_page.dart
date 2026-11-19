import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/audit_entities.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../providers/unsaved_changes.dart';
import '../widgets/new_activity_panel.dart';
import '../widgets/activity_tile.dart';
import '../widgets/daily_summary.dart';
import '../widgets/day_closure.dart';
import '../widgets/logbook_summary.dart';
import '../widgets/marked_tag.dart';

/// The logbook of the selected date, exactly as persisted on the server.
class LogbookPage extends ConsumerStatefulWidget {
  const LogbookPage({super.key});

  @override
  ConsumerState<LogbookPage> createState() => _LogbookPageState();
}

class _LogbookPageState extends ConsumerState<LogbookPage> {
  bool _opening = false;
  String? _openError;

  void _registerProgress(Activity activity) {
    ref.read(progressTargetProvider.notifier).select(activity.summary);
    ref.read(currentPageProvider.notifier).go(AppPage.progress);
  }

  void _planContinuation(Activity activity) {
    ref.read(continuationTargetProvider.notifier).select(activity.summary);
    ref.read(currentPageProvider.notifier).go(AppPage.continuation);
  }

  void _reactivate(Activity activity) {
    ref.read(reactivationTargetProvider.notifier).select(activity.summary);
    ref.read(currentPageProvider.notifier).go(AppPage.reactivation);
  }

  void _openDetail(Activity activity) {
    ref.read(activityNavProvider.notifier).open(activity.id, back: AppPage.logbook);
    ref.read(currentPageProvider.notifier).go(AppPage.activityDetail);
  }

  Future<void> _open(DateTime date) async {
    setState(() {
      _opening = true;
      _openError = null;
    });
    try {
      await ref.read(logbookProvider(date).notifier).open();
      if (mounted) setState(() => _opening = false);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _opening = false;
        _openError = errorMessage(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final date = ref.watch(selectedDateProvider);
    final view = ref.watch(logbookProvider(date));
    final day = view.value;

    final dateField = SizedBox(
      width: mobile ? double.infinity : 210,
      child: DateField(
        fieldKey: const Key('work-date'),
        label: 'Fecha laboral',
        date: date,
        onChanged: (value) {
          // Another day shows another summary: unsaved text would be lost, so the user is asked first
          ref.read(leaveRequestProvider.notifier).request(() {
            if (!mounted) return;
            setState(() => _openError = null);
            ref.read(selectedDateProvider.notifier).select(value);
          });
        },
      ),
    );

    Widget body;
    if (view.hasError && day == null) {
      final error = view.error;
      body = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la bitácora.',
        onRetry: () => ref.invalidate(logbookProvider(date)),
      );
    } else if (view.isLoading && day == null) {
      body = const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (day == null) {
      body = _NoLogbook(
        opening: _opening,
        error: _openError,
        onOpen: () => _open(date),
      );
    } else {
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LogbookSummary(logbook: day.logbook),
          const SizedBox(height: 14),
          // Closing and reopening the day. A new day (new logbook) always starts with fresh state
          DayClosure(key: ValueKey('day-closure-${day.logbook.id}'), day: day),
          const SizedBox(height: 6),
          // The audit of the day (M3-07): the closings, reopenings and changes made to it, apart from its work
          Align(
            alignment: Alignment.centerLeft,
            child: LinkButton(
              key: const Key('logbook-audit'),
              label: 'Ver auditoría de la jornada',
              onPressed: () {
                ref.read(auditTargetProvider.notifier).select(
                  type: AuditObjectType.logbook,
                  objectId: day.logbook.id,
                  title: 'Jornada del ${formatShortDate(day.logbook.date)}',
                  back: AppPage.logbook,
                );
                ref.read(currentPageProvider.notifier).go(AppPage.audit);
              },
            ),
          ),
          const SizedBox(height: 8),
          // A new day (new logbook) always starts with a fresh editor
          DailySummary(key: ValueKey('daily-summary-${day.logbook.id}'), logbook: day.logbook),
          const SizedBox(height: 22),
          const Align(
            alignment: Alignment.centerLeft,
            child: KeyedSubtree(
              key: Key('activities-heading'),
              child: KindTag(
                'Actividades y avances',
                icon: Icons.checklist_outlined,
                color: AppColors.progressText,
                background: AppColors.progressBackground,
              ),
            ),
          ),
          const SizedBox(height: 4),
          if (day.operationalActivities.isEmpty)
            const EmptyState('No hay actividades para esta selección.')
          else
            for (var i = 0; i < day.operationalActivities.length; i++)
              ActivityTile(
                key: Key('activity-${day.operationalActivities[i].id}'),
                activity: day.operationalActivities[i],
                planning: day.planningOf(day.operationalActivities[i]),
                continuations: day.continuationsOf(day.operationalActivities[i]),
                progress: day.progressOf(day.operationalActivities[i]),
                // A closed day takes no new progress: it has to be reopened first (RN-108)
                onRegisterProgress: day.logbook.closed ? null : () => _registerProgress(day.operationalActivities[i]),
                onPlanContinuation: () => _planContinuation(day.operationalActivities[i]),
                onReactivate: () => _reactivate(day.operationalActivities[i]),
                onOpen: () => _openDetail(day.operationalActivities[i]),
                first: i == 0,
              ),
          // Activities marked as registered by mistake are not part of the day's work, but they are not
          // hidden either: they stay consultable here, apart, and their mark can be reverted from the detail
          if (day.markedActivities.isNotEmpty) ...[
            const SizedBox(height: 22),
            Align(
              alignment: Alignment.centerLeft,
              child: KeyedSubtree(
                key: const Key('marked-heading'),
                child: KindTag(
                  'Registradas por error (${day.markedActivities.length})',
                  icon: Icons.report_gmailerrorred_outlined,
                  color: MarkedColors.foreground,
                  background: MarkedColors.background,
                ),
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'No cuentan en tus vistas ni recuentos y no admiten avances. Su historial se conserva.',
              key: Key('marked-note'),
              style: TextStyle(fontSize: 11, color: AppColors.textSoft),
            ),
            for (var i = 0; i < day.markedActivities.length; i++)
              ActivityTile(
                key: Key('activity-${day.markedActivities[i].id}'),
                activity: day.markedActivities[i],
                planning: day.planningOf(day.markedActivities[i]),
                continuations: day.continuationsOf(day.markedActivities[i]),
                progress: day.progressOf(day.markedActivities[i]),
                onOpen: () => _openDetail(day.markedActivities[i]),
                first: i == 0,
              ),
          ],
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Registro personal',
          title: 'Mi bitácora',
          subtitle: 'Consulta y organiza tus actividades por fecha laboral.',
          action: PrimaryButton(
            key: const Key('logbook-new-activity'),
            label: 'Nueva actividad',
            icon: Icons.add,
            onPressed: () => openNewActivity(context),
          ),
        ),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: EdgeInsets.all(mobile ? 18 : 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    PanelHeader(
                      title: 'Jornada de trabajo',
                      subtitle: 'Lo que está guardado en el servidor para esta fecha',
                      trailing: mobile ? null : dateField,
                    ),
                    if (mobile) ...[dateField, const SizedBox(height: 18)],
                    body,
                  ],
                ),
              ),
              PanelFooter(
                text: 'La planificación es distinta de un avance de ejecución.',
                action: LinkButton(
                  key: const Key('logbook-footer-new-activity'),
                  label: 'Nueva actividad →',
                  onPressed: () => openNewActivity(context),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _NoLogbook extends StatelessWidget {
  const _NoLogbook({required this.opening, required this.error, required this.onOpen});

  final bool opening;
  final String? error;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 20),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE8EDF3)),
      ),
      child: Column(
        children: [
          const Text(
            'No hay bitácora para esta fecha.',
            key: Key('no-logbook'),
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          const Text(
            'Puedes abrirla ahora, o se creará al planificar una actividad.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: Color(0xFF8292A2)),
          ),
          if (error != null) ...[
            const SizedBox(height: 10),
            Text(
              error!,
              key: const Key('open-error'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: Color(0xFFBD5954)),
            ),
          ],
          const SizedBox(height: 16),
          SecondaryButton(
            key: const Key('open-logbook'),
            label: 'Abrir bitácora',
            onPressed: opening ? null : onOpen,
          ),
        ],
      ),
    );
  }
}
