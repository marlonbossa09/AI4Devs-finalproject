import '../../../../core/utils/dates.dart';
import '../../../logbook/domain/entities/logbook_entities.dart' show ActivityOrigin, ActivityStatus;
import '../../domain/entities/report_entities.dart';

/// Wire formats of M5-01 and M5-02 (contracts version 0.2). Parsing is EXPLICIT and CLOSED: each element reads only the
/// fields the contract defines for it, so a field the app does not know (or must not show) is never carried into it. A
/// report whose collections do not agree (an entry of an activity the report does not list) is REJECTED as a whole: the app
/// never completes or repairs what the server sent.

ActivityStatus _status(Object? value) => switch (value) {
  'Pendiente' => ActivityStatus.pending,
  'En progreso' => ActivityStatus.inProgress,
  'Bloqueada' => ActivityStatus.blocked,
  'Completada' => ActivityStatus.completed,
  _ => throw FormatException('Unknown activity status: $value'),
};

List<Map<String, dynamic>> _list(Object? value) => (value as List).cast<Map<String, dynamic>>();

ReportPeriod _period(Object? value) {
  final json = value as Map<String, dynamic>;
  return ReportPeriod(from: parseDate(json['desde'] as String), to: parseDate(json['hasta'] as String));
}

ReportPerson _person(Object? value) {
  final json = value as Map<String, dynamic>;
  return ReportPerson(id: json['id'] as String, name: json['nombre'] as String);
}

ReportMetrics? _metrics(Object? value) {
  if (value == null) return null;
  final json = value as Map<String, dynamic>;
  final origin = json['actividades_por_origen'] as Map<String, dynamic>;
  final cut = json['actividades_por_estado_al_corte'] as Map<String, dynamic>;
  return ReportMetrics(
    progressEntries: json['avances'] as int,
    workdays: json['jornadas_con_registros'] as int,
    activities: json['actividades_con_registros'] as int,
    planned: origin['planificadas'] as int,
    unplanned: origin['no_planificadas'] as int,
    originUnavailable: origin['origen_no_disponible'] as int,
    withBlock: json['actividades_con_bloqueo'] as int,
    statusAtCut: StatusAtCutCounts(
      pending: cut['pendiente'] as int,
      inProgress: cut['en_progreso'] as int,
      blocked: cut['bloqueada'] as int,
      completed: cut['completada'] as int,
      unavailable: cut['estado_no_disponible'] as int,
    ),
  );
}

ReportActivity _activity(Map<String, dynamic> json) {
  switch (json['forma']) {
    case 'completa':
      return ReportActivity(
        ref: json['ref'] as String,
        isNeutral: false,
        title: json['titulo'] as String,
        origin: switch (json['origen']) {
          'planificada' => ActivityOrigin.planned,
          'no_planificada' => ActivityOrigin.unplanned,
          _ => throw FormatException('Unknown origin: ${json['origen']}'),
        },
      );
    case 'neutral':
      // Nothing else is read: a neutral activity has no title and no origin, whatever else arrived.
      return ReportActivity(ref: json['ref'] as String, isNeutral: true);
    default:
      throw FormatException('Unknown activity form: ${json['forma']}');
  }
}

ReportFact _fact(Map<String, dynamic> json) {
  final status = _status(json['estado']);
  final reason = json['motivo_bloqueo'] as String?;
  return ReportFact(
    date: parseDate(json['fecha_laboral'] as String),
    activityRef: json['actividad_ref'] as String,
    status: status,
    description: json['descripcion'] as String,
    // The reason belongs only to a Bloqueada entry: it is not carried anywhere else.
    blockReason: status == ActivityStatus.blocked ? reason : null,
  );
}

ReportBlockage _blockage(Map<String, dynamic> json) => ReportBlockage(
  activityRef: json['actividad_ref'] as String,
  occurrences: [
    for (final o in _list(json['ocurrencias'])) BlockageOccurrence(date: parseDate(o['fecha_laboral'] as String), reason: o['motivo'] as String),
  ],
);

List<String>? _narrative(Object? value) {
  if (value == null) return null;
  // Only the text of each section: nothing else of a section is read.
  return [for (final s in _list(value)) s['texto'] as String];
}

ReportBody _body(Map<String, dynamic> json) {
  final activities = [for (final a in _list(json['actividades'])) _activity(a)];
  final facts = [for (final f in _list(json['hechos'])) _fact(f)];
  final blockages = [for (final b in _list(json['bloqueos'])) _blockage(b)];
  final refs = {for (final a in activities) a.ref};
  if (refs.length != activities.length) throw const FormatException('Duplicated activity reference');
  for (final f in facts) {
    if (!refs.contains(f.activityRef)) throw const FormatException('An entry points to an activity the report does not list');
  }
  for (final b in blockages) {
    if (!refs.contains(b.activityRef)) throw const FormatException('A blockage points to an activity the report does not list');
  }
  return ReportBody(metrics: _metrics(json['agregaciones']), activities: activities, facts: facts, blockages: blockages, narrative: _narrative(json['narrativa']));
}

IndividualReport individualReportFromJson(Map<String, dynamic> json) {
  if (json['tipo'] != 'individual') throw FormatException('Unexpected report type: ${json['tipo']}');
  return IndividualReport(
    period: _period(json['periodo']),
    generatedAt: DateTime.parse(json['generado_en'] as String),
    baseStatement: json['base'] as String,
    noData: json['sin_datos'] as bool,
    person: _person(json['persona']),
    body: _body(json),
  );
}

TeamReport teamReportFromJson(Map<String, dynamic> json) {
  if (json['tipo'] != 'consolidado') throw FormatException('Unexpected report type: ${json['tipo']}');
  return TeamReport(
    period: _period(json['periodo']),
    generatedAt: DateTime.parse(json['generado_en'] as String),
    baseStatement: json['base'] as String,
    noData: json['sin_datos'] as bool,
    people: [for (final p in _list(json['personas'])) TeamReportPerson(person: _person(p['persona']), body: _body(p))],
    // The team section is read apart from the people: it is the server's sum, never recomputed here.
    teamMetrics: _metrics(json['agregaciones_del_equipo']),
  );
}
