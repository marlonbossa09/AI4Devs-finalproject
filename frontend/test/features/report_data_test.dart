import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/reports/data/remote/report_remote_data_source.dart';
import 'package:smartwork/features/reports/data/repository/report_repository_impl.dart';
import 'package:smartwork/features/reports/domain/rules/report_range_rules.dart';

import '../helpers/fakes.dart';
import '../helpers/report_fakes.dart';

ReportRepositoryImpl repoFor(FakeAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://api.test'))..httpClientAdapter = adapter;
  return ReportRepositoryImpl(ReportRemoteDataSource(ApiClient(dio: dio)));
}

Map<String, dynamic> metricsJson({int entries = 4}) => {
  'avances': entries,
  'jornadas_con_registros': 3,
  'actividades_con_registros': 2,
  'actividades_por_origen': {'planificadas': 1, 'no_planificadas': 0, 'origen_no_disponible': 1},
  'actividades_con_bloqueo': 1,
  'actividades_por_estado_al_corte': {'pendiente': 0, 'en_progreso': 1, 'bloqueada': 0, 'completada': 0, 'estado_no_disponible': 1},
};

Map<String, dynamic> bodyJson({Map<String, dynamic>? extra}) => {
  'agregaciones': metricsJson(),
  'actividades': [
    {'ref': 'a1', 'forma': 'completa', 'titulo': 'Preparar informe', 'origen': 'planificada'},
    // a neutral activity: whatever else arrives with it must NOT be read
    {'ref': 'a2', 'forma': 'neutral', 'referencia_neutral': 'Actividad en continuidad', 'titulo': 'Título que no debe leerse', 'origen': 'no_planificada'},
  ],
  'hechos': [
    {'fecha_laboral': '2026-11-03', 'actividad_ref': 'a1', 'estado': 'En progreso', 'descripcion': 'Primer avance'},
    {'fecha_laboral': '2026-11-04', 'actividad_ref': 'a1', 'estado': 'Bloqueada', 'descripcion': 'Espera datos', 'motivo_bloqueo': 'falta acceso'},
    {'fecha_laboral': '2026-11-05', 'actividad_ref': 'a2', 'estado': 'En progreso', 'descripcion': 'Continúa', 'motivo_bloqueo': 'no debe leerse'},
  ],
  'bloqueos': [
    {'actividad_ref': 'a1', 'ocurrencias': [{'fecha_laboral': '2026-11-04', 'motivo': 'falta acceso'}]},
  ],
  'narrativa': [
    {'texto': 'Primera sección.', 'refs': ['h1']},
    {'texto': 'Segunda sección.'},
  ],
  ...?extra,
};

Map<String, dynamic> individualJson({Map<String, dynamic>? body}) => {
  'tipo': 'individual',
  'periodo': {'desde': '2026-10-31', 'hasta': '2026-11-06'},
  'generado_en': '2026-11-06T14:03:22Z',
  'base': baseText,
  'sin_datos': false,
  'persona': {'id': 'p1', 'nombre': 'Carlos', 'correo': 'no-debe-leerse@ejemplo.invalid'},
  ...bodyJson(extra: body),
};

void main() {
  group('M5-01 the individual report', () {
    test('POSTs desde and hasta, and persona_id only when another person is asked for', () async {
      final adapter = FakeAdapter((_) => jsonBody(individualJson()));
      final repo = repoFor(adapter);
      await repo.generateIndividual(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect(adapter.requests.single.method, 'POST');
      expect(adapter.requests.single.path, '/api/v1/informes/individuales');
      expect(adapter.requests.single.data, {'desde': '2026-10-31', 'hasta': '2026-11-06'});
      await repo.generateIndividual(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6), personId: 'p2');
      expect(adapter.requests.last.data, {'desde': '2026-10-31', 'hasta': '2026-11-06', 'persona_id': 'p2'});
    });

    test('reads every field of the contract and nothing else: metrics, activities, entries, blockages and narrative', () async {
      final report = await repoFor(FakeAdapter((_) => jsonBody(individualJson()))).generateIndividual(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect((report.person.id, report.person.name), ('p1', 'Carlos'));
      expect(report.period.from, DateTime.utc(2026, 10, 31));
      expect(report.generatedAt, DateTime.utc(2026, 11, 6, 14, 3, 22));
      expect((report.baseStatement, report.noData), (baseText, false));
      final m = report.body.metrics!;
      expect((m.progressEntries, m.workdays, m.activities, m.planned, m.unplanned, m.originUnavailable, m.withBlock), (4, 3, 2, 1, 0, 1, 1));
      expect((m.statusAtCut.pending, m.statusAtCut.inProgress, m.statusAtCut.blocked, m.statusAtCut.completed, m.statusAtCut.unavailable), (0, 1, 0, 0, 1));
      final full = report.body.activities[0];
      expect((full.ref, full.isNeutral, full.title, full.origin), ('a1', false, 'Preparar informe', ActivityOrigin.planned));
      final neutral = report.body.activities[1];
      expect((neutral.isNeutral, neutral.title, neutral.origin), (true, null, null), reason: 'a neutral activity has no title and no origin, whatever else arrived');
      expect(report.body.facts[1].blockReason, 'falta acceso');
      expect(report.body.facts[2].blockReason, isNull, reason: 'the reason belongs only to a Bloqueada entry');
      expect(report.body.blockages.single.occurrences.single.reason, 'falta acceso');
      expect(report.body.narrative, ['Primera sección.', 'Segunda sección.'], reason: 'only the text of each section: no internal reference reaches the app');
    });

    test('a report without data keeps the base statement and has no metrics and no narrative', () async {
      final json = individualJson(body: {'agregaciones': null, 'actividades': [], 'hechos': [], 'bloqueos': [], 'narrativa': null})..['sin_datos'] = true;
      final report = await repoFor(FakeAdapter((_) => jsonBody(json))).generateIndividual(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect((report.noData, report.baseStatement), (true, baseText));
      expect((report.body.metrics, report.body.narrative), (null, null));
      expect(report.body.facts, isEmpty);
    });

    test('a report that does not agree with itself is rejected whole, never repaired', () async {
      Future<void> rejects(Map<String, dynamic> json) => expectLater(
        repoFor(FakeAdapter((_) => jsonBody(json))).generateIndividual(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6)),
        throwsA(isA<FormatException>()),
      );
      await rejects(individualJson(body: {'hechos': [{'fecha_laboral': '2026-11-03', 'actividad_ref': 'a9', 'estado': 'En progreso', 'descripcion': 'x'}]}));
      await rejects(individualJson(body: {'bloqueos': [{'actividad_ref': 'a9', 'ocurrencias': []}]}));
      await rejects(individualJson(body: {'actividades': [{'ref': 'a1', 'forma': 'completa', 'titulo': 'A', 'origen': 'planificada'}, {'ref': 'a1', 'forma': 'neutral'}]}));
      await rejects(individualJson(body: {'actividades': [{'ref': 'a1', 'forma': 'inventada'}]}));
      await rejects(individualJson(body: {'hechos': [{'fecha_laboral': '2026-11-03', 'actividad_ref': 'a1', 'estado': 'Hecho', 'descripcion': 'x'}]}));
      await rejects({...individualJson(), 'tipo': 'consolidado'});
    });
  });

  group('M5-02 the team report', () {
    test('POSTs desde and hasta only (the team is the one the user supervises)', () async {
      final adapter = FakeAdapter((_) => jsonBody({
        'tipo': 'consolidado',
        'periodo': {'desde': '2026-10-31', 'hasta': '2026-11-06'},
        'generado_en': '2026-11-06T14:03:22Z',
        'base': baseText,
        'sin_datos': true,
        'personas': [],
        'agregaciones_del_equipo': null,
      }));
      final report = await repoFor(adapter).generateTeam(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect(adapter.requests.single.method, 'POST');
      expect(adapter.requests.single.path, '/api/v1/informes/consolidados');
      expect(adapter.requests.single.data, {'desde': '2026-10-31', 'hasta': '2026-11-06'});
      expect((report.noData, report.teamMetrics, report.baseStatement), (true, null, baseText));
      expect(report.people, isEmpty);
    });

    test('reads the people, each with their own body, and the team metrics apart (never recomputed)', () async {
      final json = {
        'tipo': 'consolidado',
        'periodo': {'desde': '2026-10-31', 'hasta': '2026-11-06'},
        'generado_en': '2026-11-06T14:03:22Z',
        'base': baseText,
        'sin_datos': false,
        'personas': [
          {'persona': {'id': 'p2', 'nombre': 'Ana'}, ...bodyJson()},
          {'persona': {'id': 'p3', 'nombre': 'Beto'}, ...bodyJson()},
        ],
        'agregaciones_del_equipo': metricsJson(entries: 99),
      };
      final report = await repoFor(FakeAdapter((_) => jsonBody(json))).generateTeam(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect(report.people.map((p) => p.person.name), ['Ana', 'Beto']);
      expect(report.teamMetrics!.progressEntries, 99, reason: 'the team figure is the server\'s, not the sum of the people');
      expect(report.people[0].body.metrics!.progressEntries, 4);
      expect(report.people[1].body.narrative, hasLength(2));
    });
  });

  group('errors and rules', () {
    test('the retry metadata is read together and must agree; anything else means "no retry"', () {
      expect(notGenerated(retry: true).retryAllowed, true);
      expect(notGenerated(retry: false).retryAllowed, false);
      expect(reportError('INFORME_NO_GENERADO').retryAllowed, null);
      expect(reportError('INFORME_NO_GENERADO', details: [{'campo': 'reintento', 'reintento': true, 'motivo': 'no_aplicable'}]).retryAllowed, null, reason: 'a contradictory answer is never a reason to retry');
      expect(reportError('INFORME_NO_GENERADO', details: [{'campo': 'reintento', 'reintento': false, 'motivo': 'posible'}]).retryAllowed, null);
    });

    test('fixed texts per code: the app never shows what the server or a model said', () {
      expect(errorMessage(notGenerated(retry: true)), contains('Puedes intentarlo de nuevo'));
      expect(errorMessage(notGenerated(retry: false)), contains('no lo resolverá'));
      expect(errorMessage(notGenerated(retry: false)), isNot(contains('servidor que no debe')));
      final days = reportError('INFORME_EXCEDE_LIMITES', status: 422, details: [{'campo': 'hasta', 'motivo': 'rango_excede_el_maximo', 'maximo_dias': 31}, {'campo': 'reintento', 'reintento': false, 'motivo': 'no_aplicable'}]);
      expect(errorMessage(days), contains('como máximo 31 días'));
      final facts = reportError('INFORME_EXCEDE_LIMITES', status: 422, details: [{'campo': 'hechos', 'motivo': 'hechos_exceden_el_maximo', 'maximo_hechos': 400}]);
      expect(errorMessage(facts), contains('más de 400 registros'));
      expect(errorMessage(reportError('OPERACION_NO_PERMITIDA', status: 403)), 'Esta operación no está permitida para tu rol.');
      expect(errorMessage(reportError('RECURSO_NO_DISPONIBLE', status: 404)), 'El recurso solicitado no está disponible.');
    });

    test('the period rule: from not after to and at most 31 days with both ends included', () {
      final from = DateTime.utc(2026, 10, 1);
      expect(reportRangeProblem(from, DateTime.utc(2026, 10, 31)), isNull, reason: '31 days');
      expect(reportRangeProblem(from, DateTime.utc(2026, 11, 1)), ReportRangeProblem.tooWide, reason: '32 days');
      expect(reportRangeProblem(DateTime.utc(2026, 10, 5), DateTime.utc(2026, 10, 4)), ReportRangeProblem.fromAfterTo);
      expect(reportRangeProblem(from, from), isNull);
      expect(reportRangeMessage(ReportRangeProblem.tooWide), contains('31'));
    });
  });
}
