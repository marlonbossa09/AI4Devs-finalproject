import 'package:flutter/material.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../logbook/domain/entities/logbook_entities.dart' show ActivityOrigin;
import '../../../logbook/presentation/widgets/activity_tile.dart' show pillKind, statusLabel;
import '../../../logbook/presentation/widgets/origin_tag.dart';
import '../../../team/domain/entities/team_entities.dart' show neutralActivityLabel;
import '../../domain/entities/report_entities.dart';

/// The three kinds of content of a report are told apart by NAME (a tag with its words and an icon), never by color alone:
/// - CALCULADO: the deterministic figures, computed by the server from the authorized records;
/// - REGISTRADO: the verifiable records themselves (entries and blockages);
/// - REDACTADO CON IA: the narrative, generated text that is NOT a record and that nothing in the report depends on.
/// The app shows the generated text as PLAIN TEXT (it is untrusted content: never HTML, never a link), keeps no ranking,
/// score or comparison of people anywhere, and never completes, corrects or recomputes what the server sent.
///
/// Reading order of a report, from the most to the least verifiable: the figures (CALCULADO), the records and blockages
/// (REGISTRADO) and, last and visually apart, the narrative (REDACTADO CON IA).

const _tagCalculated = KindTag('Calculado', icon: Icons.calculate_outlined, color: AppColors.calculatedText, background: AppColors.calculatedBackground);
const _tagRecorded = KindTag('Registrado', icon: Icons.fact_check_outlined, color: AppColors.recordedText, background: AppColors.recordedBackground);
const _tagGenerated = KindTag('Redactado con IA', icon: Icons.auto_awesome, color: AppColors.generatedText, background: AppColors.generatedBackground);

/// Content width from which a report puts its records beside the blockages and the narrative.
const double reportWideBreakpoint = 820;

/// Space between the blocks of a report.
double reportGap(BuildContext context) => ScreenSize.ofContext(context).isMobile ? AppSpace.md : AppSpace.lg;

EdgeInsets _cardPadding(BuildContext context) => EdgeInsets.all(ScreenSize.ofContext(context).isMobile ? AppSpace.lg : AppSpace.xl);

/// [children] with [gap] between them.
List<Widget> _spaced(List<Widget> children, double gap) => [
  for (var i = 0; i < children.length; i++) ...[if (i > 0) SizedBox(height: gap), children[i]],
];

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

/// Title, period and moment of generation of a report, in one card. The statement of the base of the report goes in [aside]:
/// beside the title on a wide screen and under it on a narrow one. A screen reader announces it when a new report appears.
class ReportHeader extends StatelessWidget {
  const ReportHeader({super.key, required this.title, required this.period, required this.generatedAt, this.aside});

  final String title;
  final ReportPeriod period;
  final DateTime generatedAt;
  final Widget? aside;

  @override
  Widget build(BuildContext context) {
    final info = Semantics(
      liveRegion: true,
      container: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(header: true, child: Text(title, style: context.heading(AppType.cardTitle, color: AppColors.textStrong, height: 1.3))),
          const SizedBox(height: AppSpace.xs),
          Text(
            'Período del ${formatShortDate(period.from)} al ${formatShortDate(period.to)}. Generado el ${formatDateTime(generatedAt)}.',
            key: const Key('report-period'),
            style: const TextStyle(fontSize: AppType.body, height: 1.4, color: AppColors.textLabel),
          ),
        ],
      ),
    );
    return AppCard(
      padding: _cardPadding(context),
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (aside == null) return info;
          if (constraints.maxWidth >= reportWideBreakpoint - AppSpace.xxl) {
            return Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(flex: 4, child: info),
                const SizedBox(width: AppSpace.xl),
                Expanded(flex: 6, child: aside!),
              ],
            );
          }
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [info, const SizedBox(height: AppSpace.md), aside!]);
        },
      ),
    );
  }
}

/// A block of a report: a card whose header says WHAT KIND of content it holds (the tag, with its word and icon), its title
/// and, when there is one, a note under it.
class _Section extends StatelessWidget {
  const _Section({super.key, required this.tag, required this.title, required this.child, this.subtitle});

  final KindTag tag;
  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: _cardPadding(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: AppSpace.sm,
            runSpacing: AppSpace.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              tag,
              Semantics(header: true, child: Text(title, style: context.heading(AppType.bodyLarge, color: AppColors.textStrong, height: 1.3))),
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: AppSpace.xs),
            Text(subtitle!, style: const TextStyle(fontSize: AppType.caption, height: 1.4, color: AppColors.textSoft)),
          ],
          const SizedBox(height: AppSpace.md),
          child,
        ],
      ),
    );
  }
}

/// One figure, read as one sentence ("Avances: 4"). It never carries a percentage or a comparison.
class _Metric extends StatelessWidget {
  const _Metric({super.key, required this.label, required this.value});

  final String label;
  final int value;

  static const double width = 136;

  @override
  Widget build(BuildContext context) {
    return MergeSemantics(
      child: Semantics(
        label: '$label: $value',
        excludeSemantics: true,
        child: Container(
          width: width,
          padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm + 2),
          decoration: BoxDecoration(
            color: AppColors.panelFooter,
            border: Border.all(color: AppColors.border),
            borderRadius: BorderRadius.circular(AppRadius.control),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$value', style: context.heading(AppType.pageTitle, color: AppColors.textStrong, height: 1.2)),
              const SizedBox(height: 2),
              Text(label, style: const TextStyle(fontSize: AppType.caption, height: 1.3, color: AppColors.textSoft)),
            ],
          ),
        ),
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
    Widget group(String name, List<Widget> tiles) => Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(name, style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.textLabel)),
        const SizedBox(height: AppSpace.sm),
        Wrap(spacing: AppSpace.sm, runSpacing: AppSpace.sm, children: tiles),
      ],
    );
    final cut = metrics.statusAtCut;
    return _Section(
      key: Key('$prefix-metrics'),
      tag: _tagCalculated,
      title: title,
      subtitle: 'Las calcula el servidor a partir de los registros autorizados. No las redacta la IA.',
      child: Wrap(
        spacing: AppSpace.xl,
        runSpacing: AppSpace.lg,
        children: [
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
      ),
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
    return _Section(
      key: Key('$prefix-facts'),
      tag: _tagRecorded,
      title: 'Registros del período',
      subtitle: 'Cada avance con el estado que tenía cuando se registró.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [for (var i = 0; i < body.facts.length; i++) _fact(body.facts[i], i)],
      ),
    );
  }

  Widget _fact(ReportFact fact, int index) {
    final activity = body.activityOf(fact.activityRef);
    return Container(
      key: Key('$prefix-fact-$index'),
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: Border(top: BorderSide(color: index == 0 ? AppColors.border : AppColors.divider))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: AppSpace.sm,
            runSpacing: AppSpace.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(formatShortDate(fact.date), style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.textLabel)),
              StatusPill(label: statusLabel(fact.status), kind: pillKind(fact.status)),
              Text(activityName(activity), style: const TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w700, color: AppColors.textStrong)),
              if (activity != null && !activity.isNeutral && activity.origin != null) OriginTag(origin: activity.origin ?? ActivityOrigin.planned),
            ],
          ),
          const SizedBox(height: AppSpace.xs + 2),
          Text(fact.description, style: const TextStyle(fontSize: AppType.body, height: 1.45, color: AppColors.textBody)),
          if (fact.blockReason != null) ...[
            const SizedBox(height: AppSpace.xs + 2),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(padding: EdgeInsets.only(top: 1), child: Icon(Icons.block, size: 14, color: AppColors.blockedText)),
                const SizedBox(width: AppSpace.xs + 2),
                Expanded(
                  child: Text(
                    'Motivo del bloqueo: ${fact.blockReason}',
                    style: const TextStyle(fontSize: AppType.caption, height: 1.4, fontWeight: FontWeight.w600, color: AppColors.blockedText),
                  ),
                ),
              ],
            ),
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
    return _Section(
      key: Key('$prefix-blockages'),
      tag: _tagRecorded,
      title: 'Bloqueos registrados',
      subtitle: 'Registro histórico: indica cuándo se registró un bloqueo, no que la actividad siga bloqueada.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: _spaced([
          for (var i = 0; i < body.blockages.length; i++)
            Container(
              key: Key('$prefix-blockage-$i'),
              padding: const EdgeInsets.all(AppSpace.md),
              decoration: BoxDecoration(color: AppColors.blockedBackground.withValues(alpha: 0.5), borderRadius: BorderRadius.circular(AppRadius.control)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    activityName(body.activityOf(body.blockages[i].activityRef)),
                    style: const TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w700, color: AppColors.textStrong),
                  ),
                  for (final o in body.blockages[i].occurrences)
                    Padding(
                      padding: const EdgeInsets.only(top: AppSpace.xs + 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Padding(padding: EdgeInsets.only(top: 1), child: Icon(Icons.block, size: 14, color: AppColors.blockedText)),
                          const SizedBox(width: AppSpace.xs + 2),
                          Expanded(
                            child: Text('${formatShortDate(o.date)}: ${o.reason}', style: const TextStyle(fontSize: AppType.caption, height: 1.4, color: AppColors.textBody)),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
        ], AppSpace.sm),
      ),
    );
  }
}

/// The generated narrative: a list of plain-text sections, apart from the records and clearly labelled as generated text (its own
/// tint, a stripe at its edge, its tag and a warning that it is not a record). It is never presented as a verified fact. When there is
/// none, NOTHING is shown (the app never fabricates one).
class ReportNarrativeView extends StatelessWidget {
  const ReportNarrativeView({super.key, required this.sections, required this.prefix});

  final List<String> sections;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    final pad = ScreenSize.ofContext(context).isMobile ? AppSpace.lg : AppSpace.xl;
    return Container(
      key: Key('$prefix-narrative'),
      width: double.infinity,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.generatedBackground.withValues(alpha: 0.45),
        border: Border.all(color: AppColors.generatedText.withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Stack(
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(pad + AppSpace.xs, pad, pad, pad),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: AppSpace.sm,
                  runSpacing: AppSpace.xs,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    _tagGenerated,
                    Semantics(header: true, child: Text('Resumen', style: context.heading(AppType.bodyLarge, color: AppColors.textStrong, height: 1.3))),
                  ],
                ),
                const SizedBox(height: AppSpace.sm),
                const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(padding: EdgeInsets.only(top: 1), child: Icon(Icons.info_outline, size: 14, color: AppColors.generatedText)),
                    SizedBox(width: AppSpace.xs + 2),
                    Expanded(
                      child: Text(
                        'Texto generado automáticamente a partir de los registros. Puede contener errores u omisiones: la referencia son las cifras y los registros.',
                        key: Key('report-narrative-warning'),
                        style: TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.generatedText),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.md),
                // Plain text, selectable: generated content is never interpreted as markup or as a link. (`Text` inside a
                // `SelectionArea`, not `SelectableText`: the latter is not exposed to assistive technology on Flutter Web.)
                SelectionArea(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (var i = 0; i < sections.length; i++)
                        Padding(
                          padding: EdgeInsets.only(bottom: i == sections.length - 1 ? 0 : AppSpace.sm),
                          child: Text(sections[i], key: Key('$prefix-narrative-$i'), style: const TextStyle(fontSize: AppType.body, height: 1.6, color: AppColors.textBody)),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Positioned(left: 0, top: 0, bottom: 0, width: AppSpace.xs, child: const ColoredBox(color: AppColors.generatedText)),
        ],
      ),
    );
  }
}

/// What a report says about one person: figures, records, blockages and, last and apart, the narrative. On a wide screen the
/// records take the main column and the blockages and the narrative the side one; otherwise everything stacks in that order.
class ReportBodyView extends StatelessWidget {
  const ReportBodyView({super.key, required this.body, required this.prefix});

  final ReportBody body;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    final metrics = body.metrics;
    final narrative = body.narrative;
    final gap = reportGap(context);
    final facts = body.facts.isNotEmpty ? ReportFactsView(body: body, prefix: prefix) : null;
    final side = <Widget>[
      if (body.blockages.isNotEmpty) ReportBlockagesView(body: body, prefix: prefix),
      if (narrative != null && narrative.isNotEmpty) ReportNarrativeView(sections: narrative, prefix: prefix),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= reportWideBreakpoint;
        final Widget records;
        if (wide && facts != null && side.isNotEmpty) {
          final sideWidth = (constraints.maxWidth * 0.36).clamp(320.0, 400.0);
          records = Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: facts),
              SizedBox(width: gap),
              SizedBox(width: sideWidth, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: _spaced(side, gap))),
            ],
          );
        } else {
          records = Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: _spaced([?facts, ...side], gap));
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: _spaced([if (metrics != null) ReportMetricsView(metrics: metrics, prefix: prefix), records], gap),
        );
      },
    );
  }
}
