import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../logbook/domain/entities/logbook_entities.dart' show ActivityOrigin;
import '../../../logbook/presentation/widgets/activity_tile.dart' show pillKind, statusLabel;
import '../../../logbook/presentation/widgets/origin_tag.dart';
import '../../../team/domain/entities/team_entities.dart' show neutralActivityLabel;
import '../../domain/entities/report_entities.dart';

/// The three kinds of content of a report are told apart by NAME (a tag with its words), never by color alone:
/// - CALCULADO: the deterministic figures, computed by the server from the authorized records;
/// - REGISTRADO: the verifiable records themselves (entries and blockages);
/// - REDACTADO CON IA: the narrative, generated text that is NOT a record and that nothing in the report depends on.
/// The app shows the generated text as PLAIN TEXT (it is untrusted content: never HTML, never a link), keeps no ranking,
/// score or comparison of people anywhere, and never completes, corrects or recomputes what the server sent.

const _tagCalculated = KindTag('Calculado', icon: Icons.calculate_outlined, color: AppColors.calculatedText, background: AppColors.calculatedBackground);
const _tagRecorded = KindTag('Registrado', icon: Icons.fact_check_outlined, color: AppColors.recordedText, background: AppColors.recordedBackground);
const _tagGenerated = KindTag('Redactado con IA', icon: Icons.auto_awesome, color: AppColors.generatedText, background: AppColors.generatedBackground);

/// What a person reads as the name of an activity: its title, or the fixed neutral label when the activity was started in
/// another team (the server sends no title for it and the app never asks for one).
String activityName(ReportActivity? activity) {
  if (activity == null || activity.isNeutral) return neutralActivityLabel;
  return activity.title ?? neutralActivityLabel;
}

/// The fixed statement of what the report is based on (P-6). It is shown with every report, also without data.
class ReportBaseNotice extends StatelessWidget {
  const ReportBaseNotice(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Notice(title: 'Base del informe', text: text, icon: Icons.info_outline);
}

/// Title, period and moment of generation of a report.
class ReportHeader extends StatelessWidget {
  const ReportHeader({super.key, required this.title, required this.period, required this.generatedAt});

  final String title;
  final ReportPeriod period;
  final DateTime generatedAt;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppColors.textStrong)),
        const SizedBox(height: 4),
        Text(
          'Período del ${formatShortDate(period.from)} al ${formatShortDate(period.to)}. Generado el ${formatDateTime(generatedAt)}.',
          key: const Key('report-period'),
          style: const TextStyle(fontSize: 12, color: AppColors.textSoft),
        ),
      ],
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({super.key, required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 128, maxWidth: 190),
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
      decoration: BoxDecoration(color: AppColors.panelFooter, border: Border.all(color: AppColors.border), borderRadius: BorderRadius.circular(10)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$value', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textStrong)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textSoft)),
        ],
      ),
    );
  }
}

/// The six deterministic metrics, as the server calculated them. There are no percentages and nothing is derived here.
class ReportMetricsView extends StatelessWidget {
  const ReportMetricsView({super.key, required this.metrics, required this.prefix, this.title = 'Cifras del período'});

  final ReportMetrics metrics;
  final String prefix;
  final String title;

  @override
  Widget build(BuildContext context) {
    Widget group(String name, List<Widget> metricWidgets) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 10, bottom: 6),
          child: Text(name, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.textLabel)),
        ),
        Wrap(spacing: 8, runSpacing: 8, children: metricWidgets),
      ],
    );
    final cut = metrics.statusAtCut;
    return Column(
      key: Key('$prefix-metrics'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            _tagCalculated,
            Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
          ],
        ),
        const SizedBox(height: 4),
        const Text(
          'Las calcula el servidor a partir de los registros autorizados. No las redacta la IA.',
          style: TextStyle(fontSize: 11, color: AppColors.textFaint),
        ),
        group('Registros', [
          _Metric(key: Key('$prefix-metric-avances'), label: 'Avances', value: metrics.progressEntries),
          _Metric(key: Key('$prefix-metric-jornadas'), label: 'Jornadas con registros', value: metrics.workdays),
          _Metric(key: Key('$prefix-metric-actividades'), label: 'Actividades con registros', value: metrics.activities),
        ]),
        group('Actividades por origen', [
          _Metric(key: Key('$prefix-metric-planned'), label: 'Planificadas', value: metrics.planned),
          _Metric(key: Key('$prefix-metric-unplanned'), label: 'No planificadas', value: metrics.unplanned),
          _Metric(key: Key('$prefix-metric-origin-unavailable'), label: 'Origen no disponible', value: metrics.originUnavailable),
        ]),
        group('Bloqueos', [
          _Metric(key: Key('$prefix-metric-with-block'), label: 'Actividades con algún bloqueo en el período', value: metrics.withBlock),
        ]),
        group('Actividades por estado al corte (último día del período)', [
          _Metric(key: Key('$prefix-metric-cut-pending'), label: 'Pendiente', value: cut.pending),
          _Metric(key: Key('$prefix-metric-cut-progress'), label: 'En progreso', value: cut.inProgress),
          _Metric(key: Key('$prefix-metric-cut-blocked'), label: 'Bloqueada', value: cut.blocked),
          _Metric(key: Key('$prefix-metric-cut-completed'), label: 'Completada', value: cut.completed),
          _Metric(key: Key('$prefix-metric-cut-unavailable'), label: 'Estado no disponible', value: cut.unavailable),
        ]),
      ],
    );
  }
}

/// The authorized progress entries, each with the activity it belongs to and its HISTORICAL status.
class ReportFactsView extends StatelessWidget {
  const ReportFactsView({super.key, required this.body, required this.prefix});

  final ReportBody body;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: Key('$prefix-facts'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            _tagRecorded,
            const Text('Registros del período', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
          ],
        ),
        const SizedBox(height: 8),
        for (var i = 0; i < body.facts.length; i++) _fact(body.facts[i], i),
      ],
    );
  }

  Widget _fact(ReportFact fact, int index) {
    final activity = body.activityOf(fact.activityRef);
    return Container(
      key: Key('$prefix-fact-$index'),
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(border: Border.all(color: AppColors.border), borderRadius: BorderRadius.circular(10)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(formatShortDate(fact.date), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textLabel)),
              StatusPill(label: statusLabel(fact.status), kind: pillKind(fact.status)),
              Text(activityName(activity), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
              if (activity != null && !activity.isNeutral && activity.origin != null) OriginTag(origin: activity.origin ?? ActivityOrigin.planned),
            ],
          ),
          const SizedBox(height: 6),
          Text(fact.description, style: const TextStyle(fontSize: 12.5, height: 1.5, color: AppColors.textBody)),
          if (fact.blockReason != null) ...[
            const SizedBox(height: 4),
            Text('Motivo del bloqueo: ${fact.blockReason}', style: const TextStyle(fontSize: 12, height: 1.5, color: AppColors.blockedText)),
          ],
        ],
      ),
    );
  }
}

/// The blockages of each activity, grouped (P-3). They are HISTORICAL records: they do not say the activity is blocked now.
class ReportBlockagesView extends StatelessWidget {
  const ReportBlockagesView({super.key, required this.body, required this.prefix});

  final ReportBody body;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: Key('$prefix-blockages'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            _tagRecorded,
            const Text('Bloqueos registrados', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
          ],
        ),
        const SizedBox(height: 4),
        const Text(
          'Registro histórico: indica cuándo se registró un bloqueo, no que la actividad siga bloqueada.',
          style: TextStyle(fontSize: 11, color: AppColors.textFaint),
        ),
        const SizedBox(height: 8),
        for (var i = 0; i < body.blockages.length; i++)
          Container(
            key: Key('$prefix-blockage-$i'),
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: AppColors.blockedBackground.withValues(alpha: 0.5), borderRadius: BorderRadius.circular(10)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(activityName(body.activityOf(body.blockages[i].activityRef)), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
                for (final o in body.blockages[i].occurrences)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text('${formatShortDate(o.date)}: ${o.reason}', style: const TextStyle(fontSize: 12, height: 1.5, color: AppColors.textBody)),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

/// The generated narrative: a list of plain-text sections, apart from the records and clearly labelled as generated text.
/// It is never presented as a verified fact. When there is none, NOTHING is shown (the app never fabricates one).
class ReportNarrativeView extends StatelessWidget {
  const ReportNarrativeView({super.key, required this.sections, required this.prefix});

  final List<String> sections;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: Key('$prefix-narrative'),
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.generatedBackground.withValues(alpha: 0.45), border: Border.all(color: AppColors.generatedBackground), borderRadius: BorderRadius.circular(11)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _tagGenerated,
              const Text('Resumen', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Texto generado automáticamente a partir de los registros. Puede contener errores u omisiones: la referencia son las cifras y los registros.',
            key: Key('report-narrative-warning'),
            style: TextStyle(fontSize: 11, height: 1.5, color: AppColors.textSoft),
          ),
          const SizedBox(height: 8),
          // Plain text, selectable: generated content is never interpreted as markup or as a link. (`Text` inside a
          // `SelectionArea`, not `SelectableText`: the latter is not exposed to assistive technology on Flutter Web.)
          SelectionArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var i = 0; i < sections.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(sections[i], key: Key('$prefix-narrative-$i'), style: const TextStyle(fontSize: 13, height: 1.6, color: AppColors.textBody)),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// What a report says about one person: figures, records, blockages and, last and apart, the narrative.
class ReportBodyView extends StatelessWidget {
  const ReportBodyView({super.key, required this.body, required this.prefix});

  final ReportBody body;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    final metrics = body.metrics;
    final narrative = body.narrative;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (metrics != null) ReportMetricsView(metrics: metrics, prefix: prefix),
        if (body.facts.isNotEmpty) ...[const SizedBox(height: 16), ReportFactsView(body: body, prefix: prefix)],
        if (body.blockages.isNotEmpty) ...[const SizedBox(height: 8), ReportBlockagesView(body: body, prefix: prefix)],
        if (narrative != null && narrative.isNotEmpty) ...[const SizedBox(height: 10), ReportNarrativeView(sections: narrative, prefix: prefix)],
      ],
    );
  }
}
