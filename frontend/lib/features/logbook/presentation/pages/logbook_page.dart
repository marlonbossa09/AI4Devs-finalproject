import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/segmented_control.dart';
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

enum _OriginFilter { all, planned, unplanned }

/// The logbook of the selected date, exactly as persisted on the server.
///
/// Reading order: which day this is and its state (open or closed) right under the title, then the activities, which are what
/// the page is for. On a wide screen the closing, the free summary and the audit sit in a column beside the activities; on a
/// tablet or a phone they follow them (activities, summary, closing, audit).
class LogbookPage extends ConsumerStatefulWidget {
  const LogbookPage({super.key});

  @override
  ConsumerState<LogbookPage> createState() => _LogbookPageState();
}

class _LogbookPageState extends ConsumerState<LogbookPage> {
  bool _opening = false;
  String? _openError;
  _OriginFilter _filter = _OriginFilter.all;

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

  /// Another day shows another summary: unsaved text would be lost, so the user is asked first.
  void _changeDate(DateTime value) {
    ref.read(leaveRequestProvider.notifier).request(() {
      if (!mounted) return;
      setState(() {
        _openError = null;
        _filter = _OriginFilter.all;
      });
      ref.read(selectedDateProvider.notifier).select(value);
    });
  }

  @override
  Widget build(BuildContext context) {
    final size = ScreenSize.ofContext(context);
    final mobile = size.isMobile;
    final date = ref.watch(selectedDateProvider);
    final view = ref.watch(logbookProvider(date));
    final day = view.value;

    final dateControls = Row(
      mainAxisSize: mobile ? MainAxisSize.max : MainAxisSize.min,
      children: [
        IconButton(
          key: const Key('date-previous'),
          tooltip: 'Día anterior',
          icon: const Icon(Icons.chevron_left, color: AppColors.textSecondary),
          onPressed: () => _changeDate(addDays(date, -1)),
        ),
        mobile ? Expanded(child: _dateField(date)) : SizedBox(width: 210, child: _dateField(date)),
        IconButton(
          key: const Key('date-next'),
          tooltip: 'Día siguiente',
          icon: const Icon(Icons.chevron_right, color: AppColors.textSecondary),
          onPressed: () => _changeDate(addDays(date, 1)),
        ),
      ],
    );

    Widget body;
    if (view.hasError && day == null) {
      final error = view.error;
      body = AppCard(
        padding: const EdgeInsets.all(AppSpace.xxl),
        child: ErrorBox(
          message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la bitácora.',
          onRetry: () => ref.invalidate(logbookProvider(date)),
        ),
      );
    } else if (view.isLoading && day == null) {
      body = const AppCard(
        padding: EdgeInsets.all(AppSpace.xxl),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (day == null) {
      body = AppCard(
        padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xxl),
        child: _NoLogbook(opening: _opening, error: _openError, onOpen: () => _open(date)),
      );
    } else {
      final activities = _activitiesCard(day, mobile);
      final audit = _AuditCard(day: day);
      final strip = LogbookSummary(logbook: day.logbook);
      final summary = DailySummary(key: ValueKey('daily-summary-${day.logbook.id}'), logbook: day.logbook);
      final closure = DayClosure(key: ValueKey('day-closure-${day.logbook.id}'), day: day);
      body = LayoutBuilder(
        builder: (context, constraints) {
          const gap = SizedBox(height: AppSpace.lg);
          if (size.isDesktop) {
            final side = (constraints.maxWidth * 0.34).clamp(320.0, 420.0);
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [strip, gap, activities])),
                const SizedBox(width: AppSpace.xl),
                SizedBox(width: side, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [closure, gap, summary, gap, audit])),
              ],
            );
          }
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [strip, gap, activities, gap, summary, gap, closure, gap, audit]);
        },
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Registro personal',
          title: 'Mi bitácora',
          subtitle: 'Consulta y organiza tus actividades por fecha laboral.',
          action: Wrap(
            spacing: AppSpace.md,
            runSpacing: AppSpace.sm,
            crossAxisAlignment: WrapCrossAlignment.center,
            alignment: WrapAlignment.end,
            children: [
              dateControls,
              PrimaryButton(
                key: const Key('logbook-new-activity'),
                label: 'Nueva actividad',
                icon: Icons.add,
                onPressed: () => openNewActivity(context),
              ),
            ],
          ),
        ),
        body,
      ],
    );
  }

  Widget _dateField(DateTime date) => DateField(
    fieldKey: const Key('work-date'),
    label: 'Fecha laboral',
    date: date,
    onChanged: _changeDate,
  );

  /// The activities of the day with their own filter (by how they started: the counts come from the activities returned).
  Widget _activitiesCard(LogbookDay day, bool mobile) {
    final all = day.operationalActivities;
    final planned = all.where((a) => a.origin == ActivityOrigin.planned).length;
    final unplanned = all.length - planned;
    final shown = switch (_filter) {
      _OriginFilter.all => all,
      _OriginFilter.planned => all.where((a) => a.origin == ActivityOrigin.planned).toList(),
      _OriginFilter.unplanned => all.where((a) => a.origin == ActivityOrigin.unplanned).toList(),
    };
    final pad = mobile ? AppSpace.lg : AppSpace.xxl;

    Widget list;
    if (all.isEmpty) {
      list = const EmptyState('No hay actividades para esta selección.');
    } else if (shown.isEmpty) {
      list = const EmptyState('No hay actividades de este tipo en la jornada.', key: Key('logbook-filter-empty'));
    } else {
      list = Column(
        children: [
          for (var i = 0; i < shown.length; i++)
            ActivityTile(
              key: Key('activity-${shown[i].id}'),
              activity: shown[i],
              planning: day.planningOf(shown[i]),
              continuations: day.continuationsOf(shown[i]),
              progress: day.progressOf(shown[i]),
              // A closed day takes no new progress: it has to be reopened first (RN-108)
              onRegisterProgress: day.logbook.closed ? null : () => _registerProgress(shown[i]),
              onPlanContinuation: () => _planContinuation(shown[i]),
              onReactivate: () => _reactivate(shown[i]),
              onOpen: () => _openDetail(shown[i]),
              first: i == 0,
            ),
        ],
      );
    }

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: EdgeInsets.all(pad),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                KeyedSubtree(
                  key: const Key('activities-heading'),
                  child: PanelHeader(
                    title: 'Actividades y avances',
                    subtitle: 'Lo planificado y lo realizado en esta jornada',
                    bottom: all.isEmpty ? AppSpace.sm : AppSpace.md,
                  ),
                ),
                if (all.isNotEmpty)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SegmentedControl<_OriginFilter>(
                      wrap: true,
                      options: {
                        _OriginFilter.all: 'Todas ${all.length}',
                        _OriginFilter.planned: 'Planificadas $planned',
                        _OriginFilter.unplanned: 'No planificadas $unplanned',
                      },
                      selected: _filter,
                      onChanged: (value) => setState(() => _filter = value),
                    ),
                  ),
                list,
                // Activities marked as registered by mistake are not part of the day's work, but they are not
                // hidden either: they stay consultable here, apart, and their mark can be reverted from the detail
                if (day.markedActivities.isNotEmpty) ...[
                  const SizedBox(height: AppSpace.xl),
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
                  const SizedBox(height: AppSpace.xs),
                  const Text(
                    'No cuentan en tus vistas ni recuentos y no admiten avances. Su historial se conserva.',
                    key: Key('marked-note'),
                    style: TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
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
            ),
          ),
          const PanelFooter(text: 'La planificación es distinta de un avance de ejecución.'),
        ],
      ),
    );
  }
}

/// The audit of the day (M3-07): the closings, reopenings and changes made to it, apart from its work.
class _AuditCard extends ConsumerWidget {
  const _AuditCard({required this.day});

  final LogbookDay day;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.lg),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: AppSpace.md,
        children: [
          const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ExcludeSemantics(child: Icon(Icons.history, size: 20, color: AppColors.textSecondary)),
              SizedBox(width: AppSpace.sm),
              Text('Historial y auditoría', style: TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w700, color: AppColors.ink)),
            ],
          ),
          LinkButton(
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
        ],
      ),
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
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
      child: Column(
        children: [
          const Text(
            'No hay bitácora para esta fecha.',
            key: Key('no-logbook'),
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppColors.ink),
          ),
          const SizedBox(height: 6),
          const Text(
            'Puedes abrirla ahora, o se creará al planificar una actividad.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: AppColors.textSoft),
          ),
          if (error != null) ...[
            const SizedBox(height: 10),
            Text(
              error!,
              key: const Key('open-error'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: AppColors.error),
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
