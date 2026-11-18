import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/supervision/data/remote/supervision_remote_data_source.dart';
import 'package:smartwork/features/supervision/data/repository/supervision_repository_impl.dart';
import 'package:smartwork/features/supervision/domain/entities/supervision_entities.dart';

import '../helpers/fakes.dart';

SupervisionRepositoryImpl repoFor(FakeAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://api.test'))..httpClientAdapter = adapter;
  return SupervisionRepositoryImpl(SupervisionRemoteDataSource(ApiClient(dio: dio)));
}

Map<String, dynamic> fullJson(String id, {Map<String, dynamic>? extra}) => {
      'forma': 'completa', 'id': id, 'propietaria_id': 'p2', 'titulo': 'Informe', 'origen': 'planificada', 'marca_error': null,
      'fecha_laboral_origen': '2026-11-01', 'creada_en': '2026-11-01T10:00:00Z', ...?extra,
    };

Map<String, dynamic> neutralJson(String id) => {'forma': 'neutral', 'id': id, 'propietaria_id': 'p2', 'referencia_neutral': 'Actividad en continuidad'};

Map<String, dynamic> page(List<Map<String, dynamic>> elements, {String? next}) => {
      'periodo': {'desde': '2026-11-01', 'hasta': '2026-11-06'},
      'corte': '2026-11-06',
      'totales_por_estado': {'Pendiente': 1, 'En progreso': 2, 'Bloqueada': 0, 'Completada': 1},
      'sin_estado_al_corte': {'referencias_minimas': 1, 'actividades': 2},
      'elementos': elements,
      'siguiente': next,
    };

void main() {
  group('M4-03 the supervision view', () {
    test('asks /equipo/supervision with desde, hasta and the page size; the cursor only when there is one', () async {
      final adapter = FakeAdapter((_) => jsonBody(page([], next: 'c1')));
      final repo = repoFor(adapter);
      final result = await repo.getSupervision(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6));
      expect(adapter.requests.single.method, 'GET');
      expect(adapter.requests.single.path, '/api/v1/equipo/supervision');
      expect(adapter.requests.single.queryParameters, {'desde': '2026-11-01', 'hasta': '2026-11-06', 'limite': 20});
      expect(result.next, 'c1');
      await repo.getSupervision(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6), cursor: 'c1');
      expect(adapter.requests.last.queryParameters['continuar_desde'], 'c1');
      expect(adapter.requests.last.queryParameters.containsKey('corte'), false, reason: 'there is no separate cut parameter');
    });

    test('reads totals, the count apart and every element exactly as the contract defines it', () async {
      final adapter = FakeAdapter((_) => jsonBody(page([
            {'tipo': 'actividad', 'actividad': fullJson('a1'), 'propietaria_id': 'p2', 'motivo_inclusion': ['planificada_en_el_periodo', 'pendiente_al_corte'], 'estado_al_corte': 'Bloqueada', 'estado_actual_si_difiere': 'Completada'},
            {'tipo': 'actividad', 'actividad': neutralJson('a2'), 'propietaria_id': 'p2', 'motivo_inclusion': ['con_avances_en_el_periodo']},
            {'tipo': 'referencia_minima', 'actividad': neutralJson('a3'), 'propietaria_id': 'p3', 'iniciada_en_otro_equipo': true, 'estado_actual': 'En progreso', 'fecha_ultimo_avance': '2026-11-04'},
            {'tipo': 'referencia_minima', 'actividad': neutralJson('a4'), 'propietaria_id': 'p3', 'iniciada_en_otro_equipo': true, 'estado_actual': 'Pendiente'},
          ])));
      final p = await repoFor(adapter).getSupervision(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6));
      expect(p.cut, DateTime.utc(2026, 11, 6));
      expect(p.totals, {ActivityStatus.pending: 1, ActivityStatus.inProgress: 2, ActivityStatus.blocked: 0, ActivityStatus.completed: 1});
      expect((p.withoutStatus.minimalReferences, p.withoutStatus.activities), (1, 2));
      final full = p.items[0] as SupervisedActivity;
      expect(full.activity.title, 'Informe');
      expect(full.reasons, [InclusionReason.plannedInPeriod, InclusionReason.pendingAtCut]);
      expect((full.statusAtCut, full.currentStatusIfDiffers), (ActivityStatus.blocked, ActivityStatus.completed));
      final neutral = p.items[1] as SupervisedActivity;
      expect(neutral.activity.isNeutral, true);
      expect(neutral.statusAtCut, isNull, reason: 'omitted by the server: the client keeps it null and does not infer one');
      expect(neutral.currentStatusIfDiffers, isNull);
      final withDate = p.items[2] as MinimalReference;
      expect((withDate.currentStatus, withDate.lastProgressDate), (ActivityStatus.inProgress, DateTime.utc(2026, 11, 4)));
      expect((p.items[3] as MinimalReference).lastProgressDate, isNull);
    });

    test('a neutral element keeps nothing of a title, a mark or a status even if a payload carried them', () async {
      final adapter = FakeAdapter((_) => jsonBody(page([
            {'tipo': 'actividad', 'actividad': {...neutralJson('a2'), 'titulo': 'SECRETO', 'marca_error': {'motivo': 'SECRETO'}}, 'propietaria_id': 'p2', 'motivo_inclusion': ['pendiente_al_corte'], 'estado_al_corte': 'En progreso', 'equipo': 'SECRETO'},
          ])));
      final item = (await repoFor(adapter).getSupervision(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6))).items.single as SupervisedActivity;
      expect((item.activity.title, item.activity.markReason, item.activity.origin), (null, null, null));
    });

    test('an unknown element, reason or status is a format error, and a minimal reference must be neutral', () {
      final bad = [
        {'tipo': 'ranking', 'propietaria_id': 'p2'},
        {'tipo': 'actividad', 'actividad': neutralJson('a'), 'propietaria_id': 'p2', 'motivo_inclusion': ['inventado']},
        {'tipo': 'actividad', 'actividad': neutralJson('a'), 'propietaria_id': 'p2', 'motivo_inclusion': [], 'estado_al_corte': 'Casi'},
        {'tipo': 'referencia_minima', 'actividad': fullJson('a'), 'propietaria_id': 'p2', 'iniciada_en_otro_equipo': true, 'estado_actual': 'Pendiente'},
      ];
      for (final element in bad) {
        final adapter = FakeAdapter((_) => jsonBody(page([element])));
        expect(repoFor(adapter).getSupervision(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6)), throwsA(isA<FormatException>()), reason: '$element');
      }
    });

    test('access errors keep their stable code', () async {
      for (final code in ['OPERACION_NO_PERMITIDA', 'ACCESO_DESACTIVADO']) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: 403));
        expect(repoFor(adapter).getSupervision(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6)), throwsA(isA<ApiError>().having((e) => e.code, 'code', code)));
      }
    });
  });

  group('M4-04 the history of an activity', () {
    test('asks /equipo/actividades/{id} and reads a full activity with its progress and plannings in server order', () async {
      final adapter = FakeAdapter((_) => jsonBody({
            'tipo': 'actividad',
            'actividad': fullJson('a1'),
            'avances': [
              {'fecha_laboral': '2026-11-02', 'estado': 'En progreso', 'descripcion': 'Primero', 'motivo_bloqueo': null},
              {'fecha_laboral': '2026-11-05', 'estado': 'Bloqueada', 'descripcion': 'Segundo', 'motivo_bloqueo': 'Falta acceso'},
            ],
            'planificaciones': [{'fecha_laboral': '2026-11-01', 'tipo': 'original', 'descripcion': 'Plan'}],
            'estado_actual': 'Bloqueada',
          }));
      final history = (await repoFor(adapter).getActivityHistory('a1'))! as ActivityHistoryDetail;
      expect(adapter.requests.single.path, '/api/v1/equipo/actividades/a1');
      expect(history.activity.title, 'Informe');
      expect([for (final a in history.progress) (a.description, a.status, a.blockReason)], [('Primero', ActivityStatus.inProgress, null), ('Segundo', ActivityStatus.blocked, 'Falta acceso')]);
      expect(history.plannings.single.type, PlanningType.original);
      expect(history.currentStatus, ActivityStatus.blocked);
    });

    test('a neutral activity has no current status when the server omits it, and a minimal reference is only the reference', () async {
      final neutral = FakeAdapter((_) => jsonBody({'tipo': 'actividad', 'actividad': neutralJson('a2'), 'avances': [], 'planificaciones': []}));
      final h = (await repoFor(neutral).getActivityHistory('a2'))! as ActivityHistoryDetail;
      expect(h.activity.isNeutral, true);
      expect(h.currentStatus, isNull);
      expect(h.progress, isEmpty);
      expect(h.plannings, isEmpty);
      final reference = FakeAdapter((_) => jsonBody({'tipo': 'referencia_minima', 'actividad': neutralJson('a3'), 'propietaria_id': 'p3', 'iniciada_en_otro_equipo': true, 'estado_actual': 'Bloqueada', 'avances': [{'descripcion': 'NO SE LEE'}], 'titulo': 'NO SE LEE'}));
      final r = (await repoFor(reference).getActivityHistory('a3'))! as ActivityHistoryReference;
      expect((r.reference.currentStatus, r.reference.lastProgressDate, r.reference.activity.isNeutral), (ActivityStatus.blocked, null, true));
    });

    test('RECURSO_NO_DISPONIBLE is "not available" (null); a 403 is not swallowed', () async {
      final missing = FakeAdapter((_) => jsonBody({'codigo': 'RECURSO_NO_DISPONIBLE', 'mensaje': 'x', 'detalles': []}, status: 404));
      expect(await repoFor(missing).getActivityHistory('a1'), isNull);
      final forbidden = FakeAdapter((_) => jsonBody({'codigo': 'OPERACION_NO_PERMITIDA', 'mensaje': 'x', 'detalles': []}, status: 403));
      expect(repoFor(forbidden).getActivityHistory('a1'), throwsA(isA<ApiError>().having((e) => e.code, 'code', 'OPERACION_NO_PERMITIDA')));
    });
  });
}
