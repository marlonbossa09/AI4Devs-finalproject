import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/rules/report_range_rules.dart';
import '../providers/report_generation.dart';
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
    final mobile = ScreenSize.ofContext(context).isMobile;
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    _to ??= today;
    _from ??= addDays(today, -6);
    final state = ref.watch(teamReportControllerProvider);
    final busy = state.isGenerating;

    Widget body;
    if (session != null && session.role != Role.supervisor) {
      body = const EmptyState('Esta vista es solo para la supervisión del equipo.', key: Key('team-report-not-available'));
    } else {
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // While a generation runs the form cannot be changed
          IgnorePointer(ignoring: busy, child: _form(busy)),
          const SizedBox(height: 18),
          _result(state),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Informes',
          title: 'Informe del equipo',
          subtitle: 'Un resumen del trabajo registrado por tu equipo en un período, con las cifras del equipo y de cada persona.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 940),
            child: AppCard(padding: EdgeInsets.all(mobile ? 18 : 24), child: body),
          ),
        ),
      ],
    );
  }

  Widget _form(bool busy) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('team-report-from'),
                label: 'Desde',
                date: _from!,
                onChanged: (date) => setState(() {
                  _from = date;
                  _rangeError = null;
                  ref.read(teamReportControllerProvider.notifier).clear();
                }),
              ),
            ),
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('team-report-to'),
                label: 'Hasta',
                date: _to!,
                errorText: _rangeError,
                onChanged: (date) => setState(() {
                  _to = date;
                  _rangeError = null;
                  ref.read(teamReportControllerProvider.notifier).clear();
                }),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'El período abarca como máximo $maxReportRangeDays días y el informe, un máximo de registros. Generarlo hace una redacción por persona y puede tardar '
          'desde decenas de segundos hasta varios minutos.',
          key: Key('team-report-hint'),
          style: TextStyle(fontSize: 11, height: 1.5, color: AppColors.textFaint),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: PrimaryButton(
            key: const Key('team-report-submit'),
            label: busy ? 'Generando…' : 'Generar informe del equipo',
            loading: busy,
            onPressed: busy ? null : _submit,
          ),
        ),
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
        return const EmptyState('Elige un período y genera el informe del equipo.', key: Key('team-report-none'));
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
    return Column(
      key: const Key('team-report-result'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ReportHeader(title: 'Informe del equipo', period: report.period, generatedAt: report.generatedAt),
        const SizedBox(height: 12),
        ReportBaseNotice(report.baseStatement, key: const Key('team-report-base')),
        const SizedBox(height: 16),
        if (report.noData)
          const EmptyState('No hay registros de tu equipo en ese período.', key: Key('team-report-no-data'))
        else ...[
          if (metrics != null) ReportMetricsView(metrics: metrics, prefix: 'team', title: 'Cifras del equipo'),
          const SizedBox(height: 22),
          Text(
            'Personas con registros en el período (${report.people.length})',
            key: const Key('team-report-people-title'),
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AppColors.textStrong),
          ),
          const SizedBox(height: 4),
          const Text(
            'Solo aparecen las personas con al menos un registro autorizado. El orden es alfabético; no es una clasificación.',
            style: TextStyle(fontSize: 11, color: AppColors.textFaint),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < report.people.length; i++)
            Container(
              key: Key('team-report-person-$i'),
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(border: Border.all(color: AppColors.border), borderRadius: BorderRadius.circular(12)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(report.people[i].person.name, key: Key('team-report-person-$i-name'), style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppColors.textStrong)),
                  const SizedBox(height: 10),
                  ReportBodyView(body: report.people[i].body, prefix: 'team-person-$i'),
                ],
              ),
            ),
        ],
      ],
    );
  }
}
