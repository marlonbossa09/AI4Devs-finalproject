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
import '../../../../core/widgets/segmented_control.dart';
import '../../../../core/widgets/stat_card.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/domain/entities/session.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../widgets/dashboard_activity_row.dart';
import '../widgets/mini_calendar.dart';
import '../widgets/new_activity_panel.dart';

enum _Filter { all, pending }

String _plural(int n, String one, String many) => '$n ${n == 1 ? one : many}';

/// The main panel: the selected day at a glance. Everything on it comes from the logbook the server holds for that date
/// (M2-01a), with nothing computed beyond counting what it returned.
///
/// Reading order: what day this is and the one main action, how many activities the day has and in which CURRENT status,
/// the state of the day itself (open or closed), the activities, and the calendar. On a wide screen the activities are
/// beside the day and the calendar; on a tablet or a phone everything stacks.
class DashboardPage extends ConsumerStatefulWidget {
  const DashboardPage({super.key, required this.session});

  final Session session;

  @override
  ConsumerState<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends ConsumerState<DashboardPage> {
  _Filter _filter = _Filter.all;

  @override
  Widget build(BuildContext context) {
    final size = ScreenSize.ofContext(context);
    final date = ref.watch(selectedDateProvider);
    final view = ref.watch(logbookProvider(date));
    final firstName = widget.session.user.name.replaceAll(RegExp(r'\(.*?\)'), '').trim().split(' ').first;

    final activities = _ActivitiesPanel(
      view: view,
      date: date,
      filter: _filter,
      onFilter: (value) => setState(() => _filter = value),
      onRetry: () => ref.invalidate(logbookProvider(date)),
      onOpenLogbook: () => ref.read(currentPageProvider.notifier).go(AppPage.logbook),
      onRegisterProgress: (activity) {
        ref.read(progressTargetProvider.notifier).select(activity.summary);
        ref.read(currentPageProvider.notifier).go(AppPage.progress);
      },
      onReactivate: (activity) {
        ref.read(reactivationTargetProvider.notifier).select(activity.summary, back: AppPage.dashboard);
        ref.read(currentPageProvider.notifier).go(AppPage.reactivation);
      },
      onOpenActivity: (activity) {
        ref.read(activityNavProvider.notifier).open(activity.id, back: AppPage.dashboard);
        ref.read(currentPageProvider.notifier).go(AppPage.activityDetail);
      },
    );
    final journey = _JourneyCard(view: view, date: date);
    final calendar = _CalendarCard(today: widget.session.today);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DashboardHeader(firstName: firstName, date: date, today: widget.session.today),
        _Indicators(view: view, date: date),
        SizedBox(height: size.isMobile ? AppSpace.lg : AppSpace.xl),
        LayoutBuilder(
          builder: (context, constraints) {
            if (size.isDesktop) {
              final total = constraints.maxWidth - AppSpace.xl;
              final right = (total * 0.85 / 2.57).clamp(295.0, total);
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: activities),
                  const SizedBox(width: AppSpace.xl),
                  SizedBox(
                    width: right,
                    child: Column(children: [journey, const SizedBox(height: AppSpace.lg), calendar]),
                  ),
                ],
              );
            }
            final gap = SizedBox(height: size.isMobile ? AppSpace.md : AppSpace.lg);
            return Column(children: [journey, gap, activities, gap, calendar]);
          },
        ),
      ],
    );
  }
}

/// Title, one line of subtitle, the day the panel is about and the ONE main action.
class _DashboardHeader extends StatelessWidget {
  const _DashboardHeader({required this.firstName, required this.date, required this.today});

  final String firstName;
  final DateTime date;
  final DateTime today;

  /// Content width from which the date and the action fit beside the title.
  static const double _sideBySideMinWidth = 860;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final title = Row(
      children: [
        ExcludeSemantics(
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(AppRadius.card)),
            child: const Icon(Icons.today_outlined, size: 22, color: AppColors.primary),
          ),
        ),
        const SizedBox(width: AppSpace.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(header: true, child: Text('Mi jornada', style: context.heading(AppType.pageTitle, height: 1.3))),
              const SizedBox(height: 2),
              Text(
                'Hola, $firstName. Revisa tus actividades y registra tus avances.',
                style: const TextStyle(fontSize: AppType.body, color: AppColors.muted),
              ),
            ],
          ),
        ),
      ],
    );
    final chip = _DateChip(date: date, today: today);
    final action = PrimaryButton(
      key: const Key('dashboard-new-activity'),
      label: 'Nueva actividad',
      icon: Icons.add,
      onPressed: () => openNewActivity(context),
    );
    return Padding(
      padding: EdgeInsets.only(bottom: mobile ? AppSpace.lg : AppSpace.xl),
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (mobile || constraints.maxWidth < _sideBySideMinWidth) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                title,
                const SizedBox(height: AppSpace.md),
                Wrap(spacing: AppSpace.md, runSpacing: AppSpace.sm, crossAxisAlignment: WrapCrossAlignment.center, children: [chip, action]),
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: title),
              const SizedBox(width: AppSpace.lg),
              chip,
              const SizedBox(width: AppSpace.md),
              action,
            ],
          );
        },
      ),
    );
  }
}

/// The work date the whole panel is showing, with where it stands relative to today. It is information, not a control:
/// the date is changed from the calendar or from Mi bitácora.
class _DateChip extends StatelessWidget {
  const _DateChip({required this.date, required this.today});

  final DateTime date;
  final DateTime today;

  String get _relation => date == today
      ? 'Hoy'
      : date.isBefore(today)
          ? 'Jornada pasada'
          : 'Jornada futura';

  @override
  Widget build(BuildContext context) {
    final text = formatTopDate(date);
    return Semantics(
      container: true,
      label: 'Fecha laboral: $text, $_relation',
      excludeSemantics: true,
      child: Container(
        key: const Key('dashboard-date'),
        padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm),
        decoration: BoxDecoration(
          color: AppColors.white,
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(AppRadius.control),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.textSecondary),
            const SizedBox(width: AppSpace.sm),
            Flexible(
              child: Text(text, style: const TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w600, color: AppColors.ink)),
            ),
            const SizedBox(width: AppSpace.sm),
            Text(_relation, key: const Key('dashboard-date-relation'), style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
          ],
        ),
      ),
    );
  }
}

/// How many activities the day has and in which CURRENT status. The figures count what the server returned for the date:
/// the status of an activity is the last one recorded for it, wherever that was recorded. A planned activity with no
/// progress is Pendiente (that is how the status is derived), and there is no percentage anywhere.
class _Indicators extends StatelessWidget {
  const _Indicators({required this.view, required this.date});

  final AsyncValue<LogbookDay?> view;
  final DateTime date;

  @override
  Widget build(BuildContext context) {
    final size = ScreenSize.ofContext(context);
    final day = view.value;
    // Without a day yet (loading or failed) there is no figure to show: a dash, never a zero that would read as "nothing".
    final known = day != null || (!view.isLoading && !view.hasError);
    int? count(ActivityStatus status) => known ? (day?.count(status) ?? 0) : null;
    final total = known ? (day?.operationalActivities.length ?? 0) : null;

    final cards = <Widget>[
      StatCard(
        label: 'Total de actividades',
        value: total,
        caption: 'En esta jornada',
        icon: Icons.grid_view_rounded,
        compact: size.isMobile,
      ),
      StatCard(
        label: 'Pendientes',
        value: count(ActivityStatus.pending),
        caption: 'Estado actual',
        showCaption: !size.isMobile,
        icon: Icons.schedule,
        iconBackground: AppColors.pendingBackground,
        iconColor: AppColors.pendingText,
        compact: size.isMobile,
      ),
      StatCard(
        label: 'En progreso',
        value: count(ActivityStatus.inProgress),
        caption: 'Estado actual',
        showCaption: !size.isMobile,
        icon: Icons.trending_up,
        iconBackground: AppColors.progressBackground,
        iconColor: AppColors.progressText,
        compact: size.isMobile,
      ),
      StatCard(
        label: 'Bloqueadas',
        value: count(ActivityStatus.blocked),
        caption: 'Estado actual',
        showCaption: !size.isMobile,
        icon: Icons.block,
        iconBackground: AppColors.blockedBackground,
        iconColor: AppColors.blockedText,
        compact: size.isMobile,
      ),
      StatCard(
        label: 'Completadas',
        value: count(ActivityStatus.completed),
        caption: 'Estado actual',
        showCaption: !size.isMobile,
        icon: Icons.check_circle_outline,
        iconBackground: AppColors.doneBackground,
        iconColor: AppColors.doneText,
        compact: size.isMobile,
      ),
    ];

    final String summary;
    if (!known) {
      summary = view.hasError ? 'No se pudieron cargar las actividades de la jornada.' : 'Cargando las actividades de la jornada.';
    } else {
      summary = 'Jornada del ${formatLongDate(date)}: ${_plural(total!, 'actividad', 'actividades')}. '
          '${_plural(count(ActivityStatus.pending)!, 'pendiente', 'pendientes')}, '
          '${_plural(count(ActivityStatus.inProgress)!, 'en progreso', 'en progreso')}, '
          '${_plural(count(ActivityStatus.blocked)!, 'bloqueada', 'bloqueadas')}, '
          '${_plural(count(ActivityStatus.completed)!, 'completada', 'completadas')}.';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // A polite live region: when the figures change (a save, a refresh) a screen reader says what the day holds now.
        Semantics(
          liveRegion: true,
          label: summary,
          excludeSemantics: true,
          child: Padding(
            padding: const EdgeInsets.only(bottom: AppSpace.sm),
            child: const Text(
              'Estado actual de las actividades de esta jornada',
              key: Key('indicators-scope'),
              style: TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w600, color: AppColors.textSoft),
            ),
          ),
        ),
        // Five in a row on a desktop, three on a tablet (3 + 2), two on a phone (the last one takes a whole row). The cards of
        // a row are as tall as the tallest of them, so the row reads as one band.
        Builder(
          builder: (context) {
            final columns = size.isDesktop ? 5 : (size.isMobile ? 2 : 3);
            final gap = size.isMobile ? AppSpace.sm + 2 : AppSpace.md;
            final rows = <Widget>[];
            for (var start = 0; start < cards.length; start += columns) {
              final chunk = cards.sublist(start, (start + columns).clamp(0, cards.length));
              // On a phone a lone last card takes the whole row; elsewhere an incomplete row keeps the width of the others
              final fill = columns == 2 ? 0 : columns - chunk.length;
              if (rows.isNotEmpty) rows.add(SizedBox(height: gap));
              rows.add(
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (var i = 0; i < chunk.length; i++) ...[
                        if (i > 0) SizedBox(width: gap),
                        Expanded(child: chunk[i]),
                      ],
                      for (var i = 0; i < fill; i++) ...[SizedBox(width: gap), const Expanded(child: SizedBox.shrink())],
                    ],
                  ),
                ),
              );
            }
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: rows);
          },
        ),
      ],
    );
  }
}

/// Why a BLOCKED activity is blocked, as the last progress entry of this day says. Only for an activity whose current
/// status is Bloqueada, so a reason that was already lifted is never shown as current.
String? _blockReason(LogbookDay? day, Activity activity) {
  if (day == null || activity.status != ActivityStatus.blocked) return null;
  for (final entry in day.progressOf(activity).reversed) {
    if (entry.status == ActivityStatus.blocked && (entry.blockReason ?? '').isNotEmpty) return entry.blockReason;
  }
  return null;
}

class _ActivitiesPanel extends StatelessWidget {
  const _ActivitiesPanel({
    required this.view,
    required this.date,
    required this.filter,
    required this.onFilter,
    required this.onRetry,
    required this.onOpenLogbook,
    required this.onRegisterProgress,
    required this.onReactivate,
    required this.onOpenActivity,
  });

  final AsyncValue<LogbookDay?> view;
  final DateTime date;
  final _Filter filter;
  final ValueChanged<_Filter> onFilter;
  final VoidCallback onRetry;
  final VoidCallback onOpenLogbook;
  final ValueChanged<Activity> onRegisterProgress;
  final ValueChanged<Activity> onReactivate;
  final ValueChanged<Activity> onOpenActivity;

  @override
  Widget build(BuildContext context) {
    final day = view.value;
    final all = day?.operationalActivities ?? const <Activity>[];
    final shown = filter == _Filter.all ? all : all.where((a) => a.status == ActivityStatus.pending).toList();
    final mobile = ScreenSize.ofContext(context).isMobile;

    Widget body;
    if (view.hasError && day == null) {
      final error = view.error;
      body = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la bitácora.',
        onRetry: onRetry,
      );
    } else if (view.isLoading && day == null) {
      body = const Padding(
        padding: EdgeInsets.all(AppSpace.xxl + AppSpace.sm),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (shown.isEmpty) {
      final String message;
      if (all.isNotEmpty) {
        message = 'No hay actividades pendientes en esta jornada.';
      } else if (day == null) {
        message = 'Todavía no hay bitácora de esta fecha. Se crea al planificar o registrar una actividad.';
      } else {
        message = 'Esta jornada todavía no tiene actividades.';
      }
      body = EmptyState(message, key: const Key('dashboard-empty'));
    } else {
      body = Column(
        children: [
          for (var i = 0; i < shown.length; i++)
            DashboardActivityRow(
              key: Key('activity-${shown[i].id}'),
              activity: shown[i],
              planning: day?.planningOf(shown[i]),
              hasContinuation: day?.continuationsOf(shown[i]).isNotEmpty ?? false,
              hasProgress: day?.progressOf(shown[i]).isNotEmpty ?? false,
              blockReason: _blockReason(day, shown[i]),
              // A closed day takes no new progress: it has to be reopened first (RN-108)
              onRegisterProgress: day?.logbook.closed == true ? null : () => onRegisterProgress(shown[i]),
              onReactivate: () => onReactivate(shown[i]),
              onOpen: () => onOpenActivity(shown[i]),
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
            padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xxl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                PanelHeader(
                  title: 'Actividades de la jornada',
                  subtitle: 'Estado actual de cada una · ${formatShortDate(date)}',
                  trailing: SegmentedControl<_Filter>(
                    options: const {_Filter.all: 'Todas', _Filter.pending: 'Pendientes'},
                    selected: filter,
                    onChanged: onFilter,
                  ),
                ),
                body,
              ],
            ),
          ),
          PanelFooter(
            text: '${_plural(shown.length, 'actividad', 'actividades')} en esta vista',
            action: LinkButton(label: 'Ver bitácora →', onPressed: onOpenLogbook),
          ),
        ],
      ),
    );
  }
}

/// The state of the day itself: open, closed or not opened yet. It is the logbook's own state, never a progress state.
/// Closing and reopening stay where they are, in Mi bitácora, with their own conditions.
class _JourneyCard extends StatelessWidget {
  const _JourneyCard({required this.view, required this.date});

  final AsyncValue<LogbookDay?> view;
  final DateTime date;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final logbook = view.value?.logbook;
    final loading = view.isLoading && view.value == null;
    final failed = view.hasError && view.value == null;

    Widget? state;
    final String text;
    if (loading) {
      text = 'Consultando el estado de la jornada…';
    } else if (failed) {
      text = 'No se pudo consultar el estado de la jornada.';
    } else if (logbook == null) {
      state = const _NoLogbookTag();
      text = 'Todavía no hay bitácora de esta fecha. Se crea al planificar o registrar una actividad, o puedes abrirla desde Mi bitácora.';
    } else if (logbook.closed) {
      state = KeyedSubtree(key: const Key('journey-state'), child: const StatusPill(label: 'Cerrada', kind: PillKind.blocked));
      final closedAt = logbook.closedAt;
      text = 'La jornada está cerrada${closedAt == null ? '' : ' desde ${formatDateTime(closedAt)}'}. '
          'Para registrar avances hay que reabrirla desde Mi bitácora.';
    } else {
      state = KeyedSubtree(key: const Key('journey-state'), child: const StatusPill(label: 'Abierta', kind: PillKind.done));
      text = 'La jornada está abierta. El cierre se hace desde Mi bitácora.';
    }

    return AppCard(
      padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          PanelHeader(
            title: 'Jornada',
            subtitle: 'Fecha laboral: ${formatShortDate(date)}',
            trailing: state,
            bottom: AppSpace.sm,
          ),
          Text(
            text,
            key: const Key('journey-text'),
            style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
          ),
        ],
      ),
    );
  }
}

/// "Sin bitácora": the day has no logbook yet. Neutral on purpose, it is neither open nor closed.
class _NoLogbookTag extends StatelessWidget {
  const _NoLogbookTag();

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('journey-state'),
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm + 2, vertical: AppSpace.xs),
      decoration: BoxDecoration(color: AppColors.recordedBackground, borderRadius: BorderRadius.circular(AppRadius.pill)),
      child: const Text(
        'Sin bitácora',
        style: TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.recordedText),
      ),
    );
  }
}

class _CalendarCard extends ConsumerStatefulWidget {
  const _CalendarCard({required this.today});

  final DateTime today;

  @override
  ConsumerState<_CalendarCard> createState() => _CalendarCardState();
}

class _CalendarCardState extends ConsumerState<_CalendarCard> {
  late DateTime _month = _firstOf(ref.read(selectedDateProvider));

  DateTime _firstOf(DateTime date) => DateTime.utc(date.year, date.month, 1);

  void _shift(int months) => setState(() => _month = DateTime.utc(_month.year, _month.month + months, 1));

  @override
  Widget build(BuildContext context) {
    final selected = ref.watch(selectedDateProvider);
    ref.listen(selectedDateProvider, (previous, next) {
      if (next.year != _month.year || next.month != _month.month) {
        setState(() => _month = _firstOf(next));
      }
    });
    final mobile = ScreenSize.ofContext(context).isMobile;
    final pad = mobile ? AppSpace.lg : AppSpace.xl;

    return AppCard(
      padding: EdgeInsets.all(pad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          PanelHeader(
            title: 'Calendario',
            subtitle: formatMonth(_month),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  key: const Key('month-previous'),
                  tooltip: 'Mes anterior',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.chevron_left, size: 20, color: AppColors.textSecondary),
                  onPressed: () => _shift(-1),
                ),
                IconButton(
                  key: const Key('month-next'),
                  tooltip: 'Mes siguiente',
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.chevron_right, size: 20, color: AppColors.textSecondary),
                  onPressed: () => _shift(1),
                ),
              ],
            ),
          ),
          MiniCalendar(
            month: _month,
            selected: selected,
            today: widget.today,
            onSelect: (date) {
              ref.read(selectedDateProvider.notifier).select(date);
              ref.read(currentPageProvider.notifier).go(AppPage.logbook);
            },
          ),
        ],
      ),
    );
  }
}
