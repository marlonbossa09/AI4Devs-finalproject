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
import '../../../team/domain/entities/team_entities.dart';
import '../../../team/presentation/providers/team_data.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/rules/report_range_rules.dart';
import '../providers/report_generation.dart';
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
    final mobile = ScreenSize.ofContext(context).isMobile;
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    _to ??= today;
    _from ??= addDays(today, -6);
    final state = ref.watch(individualReportControllerProvider);
    final busy = state.isGenerating;
    final isSupervisor = session != null && session.role == Role.supervisor;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Informes',
          title: 'Informe individual',
          subtitle: isSupervisor
              ? 'Un resumen del trabajo registrado, tuyo o de una persona de tu equipo, en un período.'
              : 'Un resumen del trabajo que has registrado en un período.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 860),
            child: AppCard(
              padding: EdgeInsets.all(mobile ? 18 : 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // While a generation runs the form cannot be changed: nothing to cancel, nothing to mix up
                  IgnorePointer(ignoring: busy, child: _form(session?.user.id, isSupervisor, busy)),
                  const SizedBox(height: 18),
                  _result(state),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _form(String? myId, bool isSupervisor, bool busy) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (isSupervisor) ...[_personSelector(myId), const SizedBox(height: 14)],
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('report-from'),
                label: 'Desde',
                date: _from!,
                onChanged: (date) => setState(() {
                  _from = date;
                  _rangeError = null;
                  ref.read(individualReportControllerProvider.notifier).clear();
                }),
              ),
            ),
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('report-to'),
                label: 'Hasta',
                date: _to!,
                errorText: _rangeError,
                onChanged: (date) => setState(() {
                  _to = date;
                  _rangeError = null;
                  ref.read(individualReportControllerProvider.notifier).clear();
                }),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'El período abarca como máximo $maxReportRangeDays días. Generar el informe puede tardar desde decenas de segundos hasta varios minutos.',
          key: Key('report-hint'),
          style: TextStyle(fontSize: 11, height: 1.5, color: AppColors.textFaint),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: PrimaryButton(
            key: const Key('report-submit'),
            label: busy ? 'Generando…' : 'Generar informe',
            loading: busy,
            onPressed: busy ? null : _submit,
          ),
        ),
      ],
    );
  }

  Widget _personSelector(String? myId) {
    final members = ref.watch(teamMembersProvider);
    if (members.hasError && !members.isLoading) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('No se pudo cargar tu equipo. Puedes generar tu propio informe.', key: Key('report-members-error'), style: TextStyle(fontSize: 12, color: AppColors.error)),
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
        return const EmptyState('Elige un período y genera el informe.', key: Key('report-none'));
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
        ReportHeader(title: 'Informe de ${report.person.name}', period: report.period, generatedAt: report.generatedAt),
        const SizedBox(height: 12),
        ReportBaseNotice(report.baseStatement, key: const Key('report-base')),
        const SizedBox(height: 16),
        if (report.noData)
          const EmptyState('No hay datos disponibles para esta persona en ese período.', key: Key('report-no-data'))
        else
          ReportBodyView(body: report.body, prefix: 'report'),
      ],
    );
  }
}
