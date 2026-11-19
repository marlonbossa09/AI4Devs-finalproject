import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/rules/report_range_rules.dart';
import '../providers/report_generation.dart';
import '../widgets/report_form.dart';
import '../widgets/report_status_widgets.dart';
import '../widgets/report_widgets.dart';

/// The report of the team (M5-02), only for a supervisor with effective access. The server decides: a collaborator who got
/// here anyway would receive a 403 and the page itself says it is not available. The view of supervision (M4) is separate.
///
/// It shows the figures of the TEAM (deterministic, no narrative) and, for each person with at least one authorized entry, their
/// own figures, records, blockages and narrative. People without entries do not appear (they have no report). There is no ranking,
/// score or comparison of people: they are listed in the order the server gives (alphabetical), nothing is sorted here.
class TeamReportPage extends ConsumerStatefulWidget {
  const TeamReportPage({super.key});

  @override
  ConsumerState<TeamReportPage> createState() => _TeamReportPageState();
}

class _TeamReportPageState extends ConsumerState<TeamReportPage> {
  DateTime? _from;
  DateTime? _to;
  String? _rangeError;

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    _to ??= today;
    _from ??= addDays(today, -6);
    final state = ref.watch(teamReportControllerProvider);
    final busy = state.isGenerating;

    final List<Widget> body;
    if (session != null && session.role != Role.supervisor) {
      body = const [AppCard(child: EmptyState('Esta vista es solo para la supervisión del equipo.', key: Key('team-report-not-available')))];
    } else {
      body = [
        ReportForm(
          fromKey: const Key('team-report-from'),
          toKey: const Key('team-report-to'),
          from: _from!,
          to: _to!,
          onFromChanged: (date) => setState(() {
            _from = date;
            _rangeError = null;
            ref.read(teamReportControllerProvider.notifier).clear();
          }),
          onToChanged: (date) => setState(() {
            _to = date;
            _rangeError = null;
            ref.read(teamReportControllerProvider.notifier).clear();
          }),
          hint:
              'El período abarca como máximo $maxReportRangeDays días y el informe, un máximo de registros. Generarlo hace una redacción por persona y puede tardar '
              'desde decenas de segundos hasta varios minutos.',
          hintKey: const Key('team-report-hint'),
          submitKey: const Key('team-report-submit'),
          submitLabel: 'Generar informe del equipo',
          busy: busy,
          onSubmit: _submit,
          rangeError: _rangeError,
        ),
        SizedBox(height: reportGap(context)),
        _result(state),
      ];
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const PageHeader(
          eyebrow: 'Informes',
          title: 'Informe del equipo',
          subtitle: 'Un resumen del trabajo registrado por tu equipo en un período, con las cifras del equipo y de cada persona.',
        ),
        ...body,
      ],
    );
  }

  void _submit() {
    final problem = reportRangeProblem(_from!, _to!);
    if (problem != null) {
      setState(() => _rangeError = reportRangeMessage(problem));
      ref.read(teamReportControllerProvider.notifier).clear();
      return;
    }
    setState(() => _rangeError = null);
    // A new request always hides what was shown before; nothing from an earlier answer survives a rejection
    ref.read(teamReportControllerProvider.notifier).generate(from: _from!, to: _to!);
  }

  Widget _result(ReportState<TeamReport> state) {
    switch (state.phase) {
      case ReportPhase.idle:
        return const AppCard(child: EmptyState('Elige un período y genera el informe del equipo.', key: Key('team-report-none')));
      case ReportPhase.generating:
        return const ReportGenerating();
      case ReportPhase.failed:
        return ReportFailure(error: state.error!, onRetry: _submit);
      case ReportPhase.ready:
        return _TeamReportView(report: state.report!);
    }
  }
}

class _TeamReportView extends StatelessWidget {
  const _TeamReportView({required this.report});

  final TeamReport report;

  @override
  Widget build(BuildContext context) {
    final metrics = report.teamMetrics;
    final gap = reportGap(context);
    return Column(
      key: const Key('team-report-result'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ReportHeader(
          title: 'Informe del equipo',
          period: report.period,
          generatedAt: report.generatedAt,
          aside: ReportBaseNotice(report.baseStatement, key: const Key('team-report-base')),
        ),
        SizedBox(height: gap),
        if (report.noData)
          const AppCard(child: EmptyState('No hay registros de tu equipo en ese período.', key: Key('team-report-no-data')))
        else ...[
          if (metrics != null) ...[ReportMetricsView(metrics: metrics, prefix: 'team', title: 'Cifras del equipo'), SizedBox(height: gap + AppSpace.xs)],
          Semantics(
            header: true,
            child: Text(
              'Personas con registros en el período (${report.people.length})',
              key: const Key('team-report-people-title'),
              style: context.heading(AppType.cardTitle, color: AppColors.textStrong, height: 1.3),
            ),
          ),
          const SizedBox(height: AppSpace.xs),
          const Text(
            'Solo aparecen las personas con al menos un registro autorizado. El orden es alfabético; no es una clasificación.',
            style: TextStyle(fontSize: AppType.caption, height: 1.4, color: AppColors.textSoft),
          ),
          const SizedBox(height: AppSpace.md),
          for (var i = 0; i < report.people.length; i++) ...[
            if (i > 0) SizedBox(height: gap),
            _PersonBlock(index: i, person: report.people[i]),
          ],
        ],
      ],
    );
  }
}

/// One person of the team report: their name and, under it, the same blocks as the individual report. The group is a soft panel so
/// that the white blocks of one person are not mixed up with those of the next. Nothing here compares or orders people.
class _PersonBlock extends StatelessWidget {
  const _PersonBlock({required this.index, required this.person});

  final int index;
  final TeamReportPerson person;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    return Container(
      key: Key('team-report-person-$index'),
      padding: EdgeInsets.all(mobile ? AppSpace.md : AppSpace.lg),
      decoration: BoxDecoration(
        color: AppColors.background,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(AppRadius.panel),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              ExcludeSemantics(
                child: Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(color: AppColors.white, border: Border.all(color: AppColors.border), borderRadius: BorderRadius.circular(AppRadius.control)),
                  child: const Icon(Icons.person_outline, size: 18, color: AppColors.textSecondary),
                ),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Semantics(
                  header: true,
                  child: Text(person.person.name, key: Key('team-report-person-$index-name'), style: context.heading(AppType.cardTitle, color: AppColors.textStrong, height: 1.3)),
                ),
              ),
            ],
          ),
          SizedBox(height: reportGap(context)),
          ReportBodyView(body: person.body, prefix: 'team-person-$index'),
        ],
      ),
    );
  }
}
