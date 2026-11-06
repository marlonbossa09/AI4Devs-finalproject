import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/responsive_grid.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/segmented_control.dart';
import '../../../../core/widgets/stat_card.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/domain/entities/session.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../widgets/activity_tile.dart';
import '../widgets/mini_calendar.dart';

enum _Filter { all, pending }

/// Summary of the selected day: indicators, its activities, a calendar and progress.
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
    final day = view.value;
    final firstName = widget.session.user.name.replaceAll(RegExp(r'\(.*?\)'), '').trim().split(' ').first;

    final stats = ResponsiveGrid(
      columns: size.isDesktop ? 4 : 2,
      gap: size.isMobile ? 10 : 16,
      children: [
        StatCard(
          label: 'Actividades registradas',
          value: day?.activities.length ?? 0,
          caption: 'En esta jornada',
          icon: Icons.grid_view_rounded,
          compact: size.isMobile,
        ),
        StatCard(
          label: 'Pendientes',
          value: day?.count(ActivityStatus.pending) ?? 0,
          caption: 'Por atender',
          icon: Icons.schedule,
          compact: size.isMobile,
        ),
        StatCard(
          label: 'En progreso',
          value: day?.count(ActivityStatus.inProgress) ?? 0,
          caption: 'Con avances registrados',
          icon: Icons.trending_up,
          compact: size.isMobile,
        ),
        StatCard(
          label: 'Completadas',
          value: day?.count(ActivityStatus.completed) ?? 0,
          caption: 'Marcadas como finalizadas',
          icon: Icons.check,
          compact: size.isMobile,
        ),
      ],
    );

    final activities = _ActivitiesPanel(
      view: view,
      date: date,
      filter: _filter,
      onFilter: (value) => setState(() => _filter = value),
      onRetry: () => ref.invalidate(logbookProvider(date)),
      onOpenLogbook: () => ref.read(currentPageProvider.notifier).go(AppPage.logbook),
    );
    final side = _SidePanel(day: day, today: widget.session.today);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Resumen de mi trabajo',
          title: 'Buen día, $firstName',
          titleTrailing: const Icon(Icons.wb_sunny_outlined, size: 24, color: Color(0xFFE0A526)),
          subtitle: 'Revisa lo que tienes planeado y registra tus avances con claridad.',
          action: PrimaryButton(
            key: const Key('dashboard-new-planning'),
            label: 'Nueva planificación',
            icon: Icons.add,
            onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.planning),
          ),
        ),
        stats,
        const SizedBox(height: 22),
        LayoutBuilder(
          builder: (context, constraints) {
            if (size == ScreenSize.desktop) {
              final total = constraints.maxWidth - 18;
              final right = (total * 0.85 / 2.57).clamp(295.0, total);
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: activities),
                  const SizedBox(width: 18),
                  SizedBox(width: right, child: side),
                ],
              );
            }
            return Column(children: [activities, SizedBox(height: size.isMobile ? 13 : 18), side]);
          },
        ),
      ],
    );
  }
}

class _ActivitiesPanel extends StatelessWidget {
  const _ActivitiesPanel({
    required this.view,
    required this.date,
    required this.filter,
    required this.onFilter,
    required this.onRetry,
    required this.onOpenLogbook,
  });

  final AsyncValue<LogbookDay?> view;
  final DateTime date;
  final _Filter filter;
  final ValueChanged<_Filter> onFilter;
  final VoidCallback onRetry;
  final VoidCallback onOpenLogbook;

  @override
  Widget build(BuildContext context) {
    final day = view.value;
    final all = day?.activities ?? const <Activity>[];
    final shown = filter == _Filter.all
        ? all
        : all.where((a) => a.status == ActivityStatus.pending).toList();
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
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (shown.isEmpty) {
      body = const EmptyState('No hay actividades para esta selección.');
    } else {
      body = Column(
        children: [
          for (var i = 0; i < shown.length; i++)
            ActivityTile(
              key: Key('activity-${shown[i].id}'),
              activity: shown[i],
              planning: day?.planningOf(shown[i]),
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
            padding: EdgeInsets.all(mobile ? 18 : 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                PanelHeader(
                  title: 'Actividades de mi jornada',
                  subtitle: 'Un vistazo a lo que estás trabajando · ${formatShortDate(date)}',
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
            text: '${shown.length} ${shown.length == 1 ? 'actividad' : 'actividades'} en esta vista',
            action: LinkButton(label: 'Ver bitácora →', onPressed: onOpenLogbook),
          ),
        ],
      ),
    );
  }
}

class _SidePanel extends ConsumerStatefulWidget {
  const _SidePanel({required this.day, required this.today});

  final LogbookDay? day;
  final DateTime today;

  @override
  ConsumerState<_SidePanel> createState() => _SidePanelState();
}

class _SidePanelState extends ConsumerState<_SidePanel> {
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
    final day = widget.day;
    final total = day?.activities.length ?? 0;
    final done = day?.count(ActivityStatus.completed) ?? 0;
    final mobile = ScreenSize.ofContext(context).isMobile;
    final pad = mobile ? 18.0 : 24.0;

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(pad, pad, pad, 0),
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
                        icon: const Icon(Icons.chevron_left, size: 20, color: Color(0xFFA2AEBC)),
                        onPressed: () => _shift(-1),
                      ),
                      IconButton(
                        key: const Key('month-next'),
                        tooltip: 'Mes siguiente',
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(Icons.chevron_right, size: 20, color: Color(0xFFA2AEBC)),
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
          ),
          const SizedBox(height: 22),
          Container(
            padding: EdgeInsets.fromLTRB(pad, 20, pad, 0),
            decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.border))),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Estado de mis actividades', style: context.heading(15)),
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Actividades completadas',
                      style: TextStyle(fontSize: 11, color: Color(0xFF64758B)),
                    ),
                    Text(
                      '$done de $total',
                      key: const Key('completion'),
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF64758B)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: LinearProgressIndicator(
                    key: const Key('progress-bar'),
                    value: total == 0 ? 0 : done / total,
                    minHeight: 7,
                    backgroundColor: const Color(0xFFEDF4F5),
                    color: const Color(0xFF1EAA9D),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: EdgeInsets.all(pad),
            child: const Notice(
              icon: Icons.auto_awesome_outlined,
              title: 'Mantén tu historial al día',
              text: 'Registra tus planificaciones y avances en cada jornada para conservar un seguimiento claro.',
            ),
          ),
        ],
      ),
    );
  }
}
