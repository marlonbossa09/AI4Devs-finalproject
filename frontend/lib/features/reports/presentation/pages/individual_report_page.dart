import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../../team/domain/entities/team_entities.dart';
import '../../../team/presentation/providers/team_data.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/rules/report_range_rules.dart';
import '../providers/report_generation.dart';
import '../widgets/report_form.dart';
import '../widgets/report_status_widgets.dart';
import '../widgets/report_widgets.dart';

/// The individual report (M5-01): the user's own or, for a supervisor, one of their team. It decides NOTHING about
/// permissions: the person selector is only offered to a supervisor (a convenience) and the server is the authority; if it
/// says no, the screen says so and shows nothing from before. The report is read on screen: there are no editing controls.
class IndividualReportPage extends ConsumerStatefulWidget {
  const IndividualReportPage({super.key});

  @override
  ConsumerState<IndividualReportPage> createState() => _IndividualReportPageState();
}

class _IndividualReportPageState extends ConsumerState<IndividualReportPage> {
  DateTime? _from;
  DateTime? _to;

  /// Empty string = the user's own report (it sends no `persona_id`).
  String _personId = '';
  String? _rangeError;

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    _to ??= today;
    _from ??= addDays(today, -6);
    final state = ref.watch(individualReportControllerProvider);
    final busy = state.isGenerating;
    final isSupervisor = session != null && session.role == Role.supervisor;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          eyebrow: 'Informes',
          title: 'Informe individual',
          subtitle: isSupervisor
              ? 'Un resumen del trabajo registrado, tuyo o de una persona de tu equipo, en un período.'
              : 'Un resumen del trabajo que has registrado en un período.',
        ),
        ReportForm(
          fromKey: const Key('report-from'),
          toKey: const Key('report-to'),
          from: _from!,
          to: _to!,
          onFromChanged: (date) => setState(() {
            _from = date;
            _rangeError = null;
            ref.read(individualReportControllerProvider.notifier).clear();
          }),
          onToChanged: (date) => setState(() {
            _to = date;
            _rangeError = null;
            ref.read(individualReportControllerProvider.notifier).clear();
          }),
          hint: 'El período abarca como máximo $maxReportRangeDays días. Generar el informe puede tardar desde decenas de segundos hasta varios minutos.',
          hintKey: const Key('report-hint'),
          submitKey: const Key('report-submit'),
          submitLabel: 'Generar informe',
          busy: busy,
          onSubmit: _submit,
          rangeError: _rangeError,
          leading: isSupervisor ? _personSelector(session.user.id) : null,
        ),
        SizedBox(height: reportGap(context)),
        _result(state),
      ],
    );
  }

  Widget _personSelector(String? myId) {
    final members = ref.watch(teamMembersProvider);
    if (members.hasError && !members.isLoading) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'No se pudo cargar tu equipo. Puedes generar tu propio informe.',
            key: Key('report-members-error'),
            style: TextStyle(fontSize: AppType.caption, color: AppColors.error),
          ),
          LinkButton(label: 'Reintentar', onPressed: () => ref.invalidate(teamMembersProvider)),
        ],
      );
    }
    final list = members.value ?? const <TeamMember>[];
    return SelectField<String>(
      key: const Key('report-person'),
      label: 'Informe de',
      options: {'': 'Mi informe', for (final m in list) if (m.id != myId) m.id: m.role == TeamRole.supervisor ? '${m.name} (supervisión)' : m.name},
      value: _personId,
      onChanged: (id) => setState(() {
        _personId = id ?? '';
        ref.read(individualReportControllerProvider.notifier).clear();
      }),
    );
  }

  void _submit() {
    final problem = reportRangeProblem(_from!, _to!);
    if (problem != null) {
      // Not sent: the period is certain to be rejected
      setState(() => _rangeError = reportRangeMessage(problem));
      ref.read(individualReportControllerProvider.notifier).clear();
      return;
    }
    setState(() => _rangeError = null);
    // A new request always hides what was shown before; nothing from an earlier answer survives a rejection
    ref.read(individualReportControllerProvider.notifier).generate(from: _from!, to: _to!, personId: _personId.isEmpty ? null : _personId);
  }

  Widget _result(ReportState<IndividualReport> state) {
    switch (state.phase) {
      case ReportPhase.idle:
        return const AppCard(child: EmptyState('Elige un período y genera el informe.', key: Key('report-none')));
      case ReportPhase.generating:
        return const ReportGenerating();
      case ReportPhase.failed:
        return ReportFailure(error: state.error!, onRetry: _submit);
      case ReportPhase.ready:
        return _IndividualReportView(report: state.report!);
    }
  }
}

class _IndividualReportView extends StatelessWidget {
  const _IndividualReportView({required this.report});

  final IndividualReport report;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const Key('report-result'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ReportHeader(
          title: 'Informe de ${report.person.name}',
          period: report.period,
          generatedAt: report.generatedAt,
          aside: ReportBaseNotice(report.baseStatement, key: const Key('report-base')),
        ),
        SizedBox(height: reportGap(context)),
        if (report.noData)
          const AppCard(child: EmptyState('No hay datos disponibles para esta persona en ese período.', key: Key('report-no-data')))
        else
          ReportBodyView(body: report.body, prefix: 'report'),
      ],
    );
  }
}
