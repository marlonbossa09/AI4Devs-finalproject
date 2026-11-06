import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/data/models/session_model.dart';
import 'package:smartwork/features/auth/data/remote/auth_remote_data_source.dart';
import 'package:smartwork/features/auth/data/repository/auth_repository_impl.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/logbook/data/models/logbook_models.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the API contracts define (docs/api/m1 and m2).
const _logbookJson = {
  'id': 'b-1',
  'persona_id': 'p-1',
  'fecha_laboral': '2026-11-06',
  'clase_jornada': 'actual',
  'estado': 'abierta',
  'resumen': '',
  'cerrada_en': null,
  'creada_en': '2026-11-06T15:30:00Z',
  'modificada_en': '2026-11-06T15:30:00Z',
};
const _activityJson = {
  'id': 'a-1',
  'propietaria_id': 'p-1',
  'titulo': 'Preparar informe',
  'origen': 'planificada',
  'estado_actual': 'Pendiente',
  'marca_error': null,
  'fecha_laboral_origen': '2026-11-06',
  'creada_en': '2026-11-06T15:31:00Z',
};
const _planningJson = {
  'id': 'pl-1',
  'actividad_id': 'a-1',
  'fecha_laboral': '2026-11-06',
  'tipo': 'original',
  'descripcion': 'Revisar cifras',
  'registrada_en': '2026-11-06T15:31:00Z',
  'clase': 'vigente',
};

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

void main() {
  group('models (wire format -> entities)', () {
    test('session: Spanish field names map to the entity', () {
      final model = SessionModel.fromJson({
        'persona': {'id': 'p-1', 'nombre': 'Ana'},
        'rol_vigente': 'supervisor',
        'csrf_token': 'tok',
        'fecha_actual': '2026-11-06',
      });
      final session = model.toEntity();
      expect(session.user.name, 'Ana');
      expect(session.role, Role.supervisor);
      expect(session.csrf, 'tok');
      expect(session.today, DateTime.utc(2026, 11, 6));
    });

    test('sign-in response has no date: it cannot become a full session', () {
      final model = SessionModel.fromJson({
        'persona': {'id': 'p-1', 'nombre': 'Ana'},
        'rol_vigente': 'colaborador',
        'csrf_token': 'tok',
      });
      expect(model.toEntity, throwsFormatException);
    });

    test('M2-01a: logbook day with its three dates apart', () {
      final day = LogbookDayModel.fromJson({
        'bitacora': _logbookJson,
        'planificaciones': [_planningJson],
        'avances': <dynamic>[],
        'actividades': [_activityJson],
      }).toEntity();
      expect(day.logbook.date, DateTime.utc(2026, 11, 6));
      expect(day.logbook.dateType, DateType.today);
      expect(day.logbook.closed, isFalse);
      expect(day.logbook.createdAt, DateTime.utc(2026, 11, 6, 15, 30));
      expect(day.logbook.updatedAt, DateTime.utc(2026, 11, 6, 15, 30));
      expect(day.plannings.single.type, PlanningType.original);
      expect(day.activities.single.status, ActivityStatus.pending);
      expect(day.activities.single.title, 'Preparar informe');
    });

    test('M2-03: planning result', () {
      final result = PlanResultModel.fromJson({
        'actividad': _activityJson,
        'planificacion': _planningJson,
        'bitacora_creada': true,
      }).toEntity();
      expect(result.logbookCreated, isTrue);
      expect(result.activity.origin, ActivityOrigin.planned);
      expect(result.planning.description, 'Revisar cifras');
    });

    test('the four states map; an unknown one is rejected', () {
      const map = {
        'Pendiente': ActivityStatus.pending,
        'En progreso': ActivityStatus.inProgress,
        'Bloqueada': ActivityStatus.blocked,
        'Completada': ActivityStatus.completed,
      };
      map.forEach((wire, status) {
        final a = ActivityModel.fromJson({..._activityJson, 'estado_actual': wire}).toEntity();
        expect(a.status, status);
      });
      expect(
        () => ActivityModel.fromJson({..._activityJson, 'estado_actual': 'Otro'}).toEntity(),
        throwsFormatException,
      );
    });

    test('an activity with an error mark is flagged', () {
      final a = ActivityModel.fromJson({
        ..._activityJson,
        'marca_error': {'motivo': 'x', 'marcada_en': '2026-11-06T16:00:00Z'},
      }).toEntity();
      expect(a.marked, isTrue);
    });
  });

  group('logbook repository over the wire', () {
    test('no logbook (RECURSO_NO_DISPONIBLE) is a normal null, not an error', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({'codigo': 'RECURSO_NO_DISPONIBLE', 'mensaje': 'x', 'detalles': []}, status: 404),
      );
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      expect(await repo.getLogbook(DateTime.utc(2026, 11, 6)), isNull);
      expect(adapter.requests.single.method, 'GET');
      expect(adapter.requests.single.path, '/api/v1/mi/bitacoras/2026-11-06');
    });

    test('other failures are not swallowed', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({'codigo': 'SIN_PERTENENCIA_VIGENTE', 'mensaje': 'x', 'detalles': []}, status: 403),
      );
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      await expectLater(
        repo.getLogbook(DateTime.utc(2026, 11, 6)),
        throwsA(isA<ApiError>().having((f) => f.code, 'code', 'SIN_PERTENENCIA_VIGENTE')),
      );
    });

    test('open sends the work date in the body', () async {
      final adapter = FakeAdapter((_) => jsonBody({'creada': true, 'bitacora': _logbookJson}, status: 201));
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      final result = await repo.openLogbook(DateTime.utc(2026, 11, 6));
      expect(result.created, isTrue);
      final request = adapter.requests.single;
      expect(request.path, '/api/v1/mi/bitacoras');
      expect(request.data, {'fecha_laboral': '2026-11-06'});
    });

    test('plan sends title, description, the CSRF token and the idempotency key', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({'actividad': _activityJson, 'planificacion': _planningJson, 'bitacora_creada': false}, status: 201),
      );
      final client = _client(adapter)..csrf = 'csrf-9';
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(client));
      await repo.createActivity(
        date: DateTime.utc(2026, 11, 6),
        title: 'Preparar informe',
        description: 'Revisar cifras',
        key: 'key-1',
      );
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/bitacoras/2026-11-06/planificaciones');
      expect(request.headers['Idempotency-Key'], 'key-1');
      expect(request.headers['X-CSRF-Token'], 'csrf-9');
      expect(request.data, {'titulo': 'Preparar informe', 'descripcion': 'Revisar cifras'});
      expect(jsonEncode(request.data), isNot(contains('estado')));
    });

    test('the description is omitted when empty', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({'actividad': _activityJson, 'planificacion': _planningJson, 'bitacora_creada': false}, status: 201),
      );
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      await repo.createActivity(date: parseDate('2026-11-06'), title: 'T', key: 'k');
      expect(adapter.requests.single.data, {'titulo': 'T'});
    });
  });

  group('auth repository over the wire', () {
    Map<String, dynamic> session() => {
      'persona': {'id': 'p-1', 'nombre': 'Ana'},
      'rol_vigente': 'colaborador',
      'csrf_token': 'tok-1',
      'fecha_actual': '2026-11-06',
    };

    test('sign in posts the credentials, then reads the session and keeps the CSRF token in memory', () async {
      final adapter = FakeAdapter((o) {
        if (o.method == 'POST') {
          return jsonBody({'persona': session()['persona'], 'rol_vigente': 'colaborador', 'csrf_token': 'tok-1'}, status: 201);
        }
        return jsonBody(session());
      });
      final client = _client(adapter);
      final repo = AuthRepositoryImpl(AuthRemoteDataSource(client), client);
      final result = await repo.login(user: 'ana', password: 'secreta-123');
      expect(adapter.requests.map((r) => r.method), ['POST', 'GET']);
      expect(adapter.requests.first.data, {'identificador_acceso': 'ana', 'contrasena': 'secreta-123'});
      expect(result.today, DateTime.utc(2026, 11, 6));
      expect(client.csrf, 'tok-1');
    });

    test('no session (NO_IDENTIFICADA) is a normal null and clears the token', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({'codigo': 'NO_IDENTIFICADA', 'mensaje': 'x', 'detalles': []}, status: 401),
      );
      final client = _client(adapter)..csrf = 'viejo';
      final repo = AuthRepositoryImpl(AuthRemoteDataSource(client), client);
      expect(await repo.getSession(), isNull);
      expect(client.csrf, isNull);
    });

    test('sign out forgets the token even if the server call fails', () async {
      final adapter = FakeAdapter((o) => throw DioException(requestOptions: o, type: DioExceptionType.connectionError));
      final client = _client(adapter)..csrf = 'tok';
      final repo = AuthRepositoryImpl(AuthRemoteDataSource(client), client);
      await expectLater(repo.logout(), throwsA(isA<ApiError>()));
      expect(client.csrf, isNull);
    });
  });
}
