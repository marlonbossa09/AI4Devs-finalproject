import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/team/data/remote/team_remote_data_source.dart';
import 'package:smartwork/features/team/data/repository/team_repository_impl.dart';
import 'package:smartwork/features/team/domain/entities/team_entities.dart';
import 'package:smartwork/features/team/domain/rules/history_range_rules.dart';
import 'package:dio/dio.dart';

import '../helpers/fakes.dart';

TeamRepositoryImpl repoFor(FakeAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://api.test'))..httpClientAdapter = adapter;
  return TeamRepositoryImpl(TeamRemoteDataSource(ApiClient(dio: dio)));
}

void main() {
  group('M4-05 members', () {
    test('reads exactly persona_id, nombre and rol, from GET /equipo/integrantes with the largest page', () async {
      final adapter = FakeAdapter((_) => jsonBody({
            'elementos': [
              {'persona_id': 'p2', 'nombre': 'Ana', 'rol': 'colaborador', 'correo': 'no-se-lee@x.test'},
              {'persona_id': 'p3', 'nombre': 'Sara', 'rol': 'supervisor'},
            ],
            'siguiente': 'c1',
          }));
      final page = await repoFor(adapter).listMembers();
      expect(adapter.requests.single.method, 'GET');
      expect(adapter.requests.single.path, '/api/v1/equipo/integrantes');
      expect(adapter.requests.single.queryParameters, {'limite': 100});
      expect([for (final m in page.items) (m.id, m.name, m.role)], [('p2', 'Ana', TeamRole.collaborator), ('p3', 'Sara', TeamRole.supervisor)]);
      expect(page.next, 'c1');
      await repoFor(adapter).listMembers(cursor: 'c1');
      expect(adapter.requests.last.queryParameters, {'limite': 100, 'continuar_desde': 'c1'});
    });

    test('an unknown role is a format error, not a guess', () async {
      final adapter = FakeAdapter((_) => jsonBody({'elementos': [{'persona_id': 'p2', 'nombre': 'Ana', 'rol': 'jefe'}], 'siguiente': null}));
      expect(repoFor(adapter).listMembers(), throwsA(isA<FormatException>()));
    });
  });

  group('M4-01 a colleague logbook', () {
    Map<String, dynamic> body(List<Map<String, dynamic>> activities) => {
          'bitacora': {'id': 'b1', 'persona_id': 'p2', 'fecha_laboral': '2026-11-06', 'clase_jornada': 'actual', 'estado': 'abierta', 'resumen': 'Hola', 'cerrada_en': null, 'creada_en': '2026-11-06T10:00:00Z', 'modificada_en': '2026-11-06T10:00:00Z'},
          'planificaciones': [{'id': 'pl1', 'actividad_id': 'a1', 'fecha_laboral': '2026-11-06', 'tipo': 'original', 'descripcion': 'Plan', 'registrada_en': '2026-11-06T10:00:00Z', 'clase': 'vigente'}],
          'avances': [{'id': 'v1', 'actividad_id': 'a1', 'fecha_laboral': '2026-11-06', 'estado': 'Bloqueada', 'descripcion': 'Hice', 'motivo_bloqueo': 'Falta acceso', 'es_reactivacion': false, 'registrado_en': '2026-11-06T10:00:00Z', 'modificado_en': '2026-11-06T10:00:00Z'}],
          'actividades': activities,
        };

    test('asks /personas/{id}/bitacoras/{fecha} and reads full and neutral activities', () async {
      final adapter = FakeAdapter((_) => jsonBody(body([
            {'forma': 'completa', 'id': 'a1', 'propietaria_id': 'p2', 'titulo': 'Informe', 'origen': 'planificada', 'marca_error': null, 'fecha_laboral_origen': '2026-11-06', 'creada_en': '2026-11-06T10:00:00Z'},
            {'forma': 'neutral', 'id': 'a2', 'propietaria_id': 'p2', 'referencia_neutral': 'Actividad en continuidad'},
          ])));
      final logbook = (await repoFor(adapter).getPeerLogbook(personId: 'p2', date: DateTime.utc(2026, 11, 6)))!;
      expect(adapter.requests.single.path, '/api/v1/personas/p2/bitacoras/2026-11-06');
      expect(logbook.closed, false);
      expect(logbook.activities[0].form, ActivityForm.full);
      expect(logbook.activities[0].title, 'Informe');
      expect(logbook.activities[0].status, isNull, reason: 'estado_actual is omitted when the owner is not in the team');
      expect(logbook.activities[1].form, ActivityForm.neutral);
      expect(logbook.progress.single.blockReason, 'Falta acceso');
      expect(logbook.progress.single.status, ActivityStatus.blocked);
    });

    test('a neutral activity is read as neutral even if a payload carried a title or a mark: nothing of them is kept', () async {
      final adapter = FakeAdapter((_) => jsonBody(body([
            {'forma': 'neutral', 'id': 'a2', 'propietaria_id': 'p2', 'referencia_neutral': 'x', 'titulo': 'SECRETO', 'marca_error': {'motivo': 'SECRETO'}, 'estado_actual': 'Bloqueada'},
          ])));
      final activity = (await repoFor(adapter).getPeerLogbook(personId: 'p2', date: DateTime.utc(2026, 11, 6)))!.activities.single;
      expect(activity.isNeutral, true);
      expect(activity.title, isNull);
      expect(activity.markReason, isNull);
      expect(activity.status, isNull);
      expect(activity.origin, isNull);
    });

    test('RECURSO_NO_DISPONIBLE is "not available" (null); other errors are not swallowed', () async {
      final missing = FakeAdapter((_) => jsonBody({'codigo': 'RECURSO_NO_DISPONIBLE', 'mensaje': 'x', 'detalles': []}, status: 404));
      expect(await repoFor(missing).getPeerLogbook(personId: 'p2', date: DateTime.utc(2026, 11, 6)), isNull);
      final forbidden = FakeAdapter((_) => jsonBody({'codigo': 'ACCESO_DESACTIVADO', 'mensaje': 'x', 'detalles': []}, status: 403));
      expect(repoFor(forbidden).getPeerLogbook(personId: 'p2', date: DateTime.utc(2026, 11, 6)), throwsA(isA<ApiError>().having((e) => e.code, 'code', 'ACCESO_DESACTIVADO')));
    });
  });

  group('M4-02 history', () {
    Map<String, dynamic> page(String? next) => {
          'elementos': [
            {'persona_id': 'p2', 'fecha_laboral': '2026-11-05', 'estado': 'cerrada', 'resumen': 'R', 'actividades': [{'forma': 'neutral', 'id': 'a2', 'propietaria_id': 'p2', 'referencia_neutral': 'x'}]},
          ],
          'siguiente': next,
        };

    test('ALWAYS sends desde and hasta; persona_id only when chosen; the cursor only when there is one', () async {
      final adapter = FakeAdapter((_) => jsonBody(page('c1')));
      final repo = repoFor(adapter);
      final result = await repo.getHistory(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6));
      expect(adapter.requests.single.path, '/api/v1/historico');
      expect(adapter.requests.single.queryParameters, {'desde': '2026-11-01', 'hasta': '2026-11-06', 'limite': 20});
      expect(result.next, 'c1');
      expect(result.items.single.closed, true);
      expect(result.items.single.activities.single.isNeutral, true);
      await repo.getHistory(from: DateTime.utc(2026, 11, 1), to: DateTime.utc(2026, 11, 6), personId: 'p2', cursor: 'c1');
      expect(adapter.requests.last.queryParameters, {'desde': '2026-11-01', 'hasta': '2026-11-06', 'persona_id': 'p2', 'limite': 20, 'continuar_desde': 'c1'});
    });
  });

  group('range rules and messages', () {
    test('92 days are allowed (both ends included) and 93 are not', () {
      final from = DateTime.utc(2026, 8, 1);
      expect(rangeDays(from, addDays(from, 91)), 92);
      expect(historyRangeProblem(from, addDays(from, 91)), isNull);
      expect(historyRangeProblem(from, addDays(from, 92)), HistoryRangeProblem.tooWide);
      expect(historyRangeProblem(from, from), isNull);
      expect(historyRangeProblem(addDays(from, 1), from), HistoryRangeProblem.fromAfterTo);
    });

    test('the server wording of a rejected range and of a forbidden operation are fixed texts', () {
      const wide = ApiError(code: 'SOLICITUD_INVALIDA', message: 'x', details: [{'campo': 'hasta', 'motivo': 'rango_excede_el_maximo', 'maximo_dias': 30}]);
      expect(errorMessage(wide), 'El rango puede abarcar como máximo 30 días.');
      expect(errorMessage(const ApiError(code: 'SOLICITUD_INVALIDA', message: 'x')), 'La solicitud no es válida.');
      expect(errorMessage(const ApiError(code: 'OPERACION_NO_PERMITIDA', message: 'PAYLOAD')), 'Esta operación no está permitida para tu rol.');
    });
  });
}
