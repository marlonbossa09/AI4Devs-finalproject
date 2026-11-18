import 'dart:async';

import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/reports/domain/entities/report_entities.dart';
import 'package:smartwork/features/reports/domain/repository/report_repository.dart';

/// In-memory "server" of the reports. It records what the screen asked for and can HOLD an answer (to see the screen
/// while a generation is running). An answer is an [IndividualReport]/[TeamReport] or an [ApiError] to throw.
class FakeReportRepository implements ReportRepository {
  Object? individualAnswer;
  Object? teamAnswer;

  /// While set, every answer waits for it (a generation "in progress").
  Completer<void>? gate;

  final List<Map<String, Object?>> individualRequests = [];
  final List<Map<String, Object?>> teamRequests = [];

  @override
  Future<IndividualReport> generateIndividual({required DateTime from, required DateTime to, String? personId}) async {
    individualRequests.add({'from': from, 'to': to, 'personId': personId});
    await gate?.future;
    final answer = individualAnswer;
    if (answer is ApiError) throw answer;
    return answer as IndividualReport;
  }

  @override
  Future<TeamReport> generateTeam({required DateTime from, required DateTime to}) async {
    teamRequests.add({'from': from, 'to': to});
    await gate?.future;
    final answer = teamAnswer;
    if (answer is ApiError) throw answer;
    return answer as TeamReport;
  }
}

const _noBlocks = StatusAtCutCounts(pending: 0, inProgress: 0, blocked: 0, completed: 0, unavailable: 0);

ReportMetrics sampleMetrics({int entries = 4, int workdays = 3, int activities = 2, StatusAtCutCounts? cut}) => ReportMetrics(
  progressEntries: entries,
  workdays: workdays,
  activities: activities,
  planned: 1,
  unplanned: 0,
  originUnavailable: 1,
  withBlock: 1,
  statusAtCut: cut ?? const StatusAtCutCounts(pending: 0, inProgress: 1, blocked: 0, completed: 0, unavailable: 1),
);

/// A body with a full activity (a1, with a blockage) and a neutral one (a2: started in another team).
ReportBody sampleBody({List<String>? narrative = const ['Resumen redactado a partir de los registros.']}) => ReportBody(
  metrics: sampleMetrics(),
  activities: const [
    ReportActivity(ref: 'a1', isNeutral: false, title: 'Preparar informe mensual', origin: ActivityOrigin.planned),
    ReportActivity(ref: 'a2', isNeutral: true),
  ],
  facts: [
    ReportFact(date: DateTime.utc(2026, 11, 3), activityRef: 'a1', status: ActivityStatus.inProgress, description: 'Primer avance del informe'),
    ReportFact(
      date: DateTime.utc(2026, 11, 4),
      activityRef: 'a1',
      status: ActivityStatus.blocked,
      description: 'Espera datos del cliente',
      blockReason: 'falta acceso al servidor',
    ),
    ReportFact(date: DateTime.utc(2026, 11, 5), activityRef: 'a2', status: ActivityStatus.inProgress, description: 'Continúa el trabajo en este equipo'),
  ],
  blockages: [
    ReportBlockage(
      activityRef: 'a1',
      occurrences: [BlockageOccurrence(date: DateTime.utc(2026, 11, 4), reason: 'falta acceso al servidor')],
    ),
  ],
  narrative: narrative,
);

const emptyBody = ReportBody(metrics: null, activities: [], facts: [], blockages: [], narrative: null);

final _period = ReportPeriod(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
const baseText = 'Este informe se basa únicamente en los registros disponibles y autorizados del período y no representa información que nunca fue registrada.';

IndividualReport sampleIndividual({String name = 'Carlos Colaborador (demo)', String id = 'p1', bool noData = false, List<String>? narrative = const ['Resumen redactado a partir de los registros.']}) =>
    IndividualReport(
      period: _period,
      generatedAt: DateTime.utc(2026, 11, 6, 14, 3, 22),
      baseStatement: baseText,
      noData: noData,
      person: ReportPerson(id: id, name: name),
      body: noData ? emptyBody : sampleBody(narrative: narrative),
    );

TeamReport sampleTeam({bool noData = false}) => TeamReport(
  period: _period,
  generatedAt: DateTime.utc(2026, 11, 6, 14, 3, 22),
  baseStatement: baseText,
  noData: noData,
  people: noData
      ? const []
      : [
          TeamReportPerson(person: const ReportPerson(id: 'p2', name: 'Ana Compañera'), body: sampleBody(narrative: const ['Ana trabajó en el informe mensual.'])),
          TeamReportPerson(person: const ReportPerson(id: 'p3', name: 'Sara Supervisora'), body: sampleBody(narrative: const ['Sara registró avances.'])),
        ],
  teamMetrics: noData ? null : sampleMetrics(entries: 8, workdays: 4, activities: 4, cut: _noBlocks),
);

/// The reply of the server to a report that cannot be generated, as the contract defines it.
ApiError reportError(String code, {List<Map<String, dynamic>> details = const [], int status = 503}) =>
    ApiError(code: code, message: 'texto del servidor que no debe mostrarse', details: details, status: status);

ApiError notGenerated({required bool retry}) => reportError('INFORME_NO_GENERADO', details: [
  {'campo': 'reintento', 'reintento': retry, 'motivo': retry ? 'posible' : 'no_aplicable'},
]);
