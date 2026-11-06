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

const _progressJson = {
  'id': 'av-1',
  'actividad_id': 'a-1',
  'fecha_laboral': '2026-11-05',
  'estado': 'Bloqueada',
  'descripcion': 'Esperando datos',
  'motivo_bloqueo': 'Falta el acceso',
  'es_reactivacion': false,
  'registrado_en': '2026-11-06T16:00:00Z',
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

    test('M2-01a: the progress entries of the day keep their own status, date and reason', () {
      final day = LogbookDayModel.fromJson({
        'bitacora': _logbookJson,
        'planificaciones': [_planningJson],
        'avances': [_progressJson],
        'actividades': [_activityJson],
      }).toEntity();
      final entry = day.progress.single;
      expect(entry.status, ActivityStatus.blocked);
      expect(entry.date, DateTime.utc(2026, 11, 5));
      expect(entry.description, 'Esperando datos');
      expect(entry.blockReason, 'Falta el acceso');
      expect(entry.isReactivation, isFalse);
      expect(day.progressOf(day.activities.single), [entry]);
    });

    test('M2-01a: a day without the avances list has no progress', () {
      final day = LogbookDayModel.fromJson({
        'bitacora': _logbookJson,
        'planificaciones': <dynamic>[],
        'actividades': <dynamic>[],
      }).toEntity();
      expect(day.progress, isEmpty);
    });

    test('M2-05: progress result with the recalculated activity', () {
      final result = ProgressResultModel.fromJson({
        'avance': {..._progressJson, 'estado': 'En progreso', 'motivo_bloqueo': null},
        'actividad': {..._activityJson, 'estado_actual': 'En progreso'},
        'bitacora_creada': true,
      }).toEntity();
      expect(result.progress.status, ActivityStatus.inProgress);
      expect(result.progress.blockReason, isNull);
      expect(result.activity.status, ActivityStatus.inProgress);
      expect(result.logbookCreated, isTrue);
    });

    test('statuses go to the wire with the exact contract names', () {
      expect({for (final s in ActivityStatus.values) s: statusToWire(s)}, {
        ActivityStatus.pending: 'Pendiente',
        ActivityStatus.inProgress: 'En progreso',
        ActivityStatus.blocked: 'Bloqueada',
        ActivityStatus.completed: 'Completada',
      });
    });

    test('M2-07: the detail keeps what was planned apart from what was done, in sequence order', () {
      final detail = ActivityDetailModel.fromJson({
        'actividad': _activityJson,
        'planificacion_original': _planningJson,
        'continuaciones_planificadas': [
          {..._planningJson, 'id': 'pl-2', 'tipo': 'continuacion', 'fecha_laboral': '2026-11-09', 'descripcion': 'Seguir'},
        ],
        'avances': [
          {..._progressJson, 'id': 'av-1', 'fecha_laboral': '2026-11-04', 'estado': 'En progreso', 'motivo_bloqueo': null},
          {..._progressJson, 'id': 'av-2', 'fecha_laboral': '2026-11-05'},
        ],
        'estado_actual': 'Bloqueada',
      }).toEntity();
      expect(detail.originalPlanning!.type, PlanningType.original);
      expect(detail.plannedContinuations.single.type, PlanningType.continuation);
      expect(detail.plannedContinuations.single.date, DateTime.utc(2026, 11, 9));
      expect([for (final p in detail.progress) p.id], ['av-1', 'av-2']); // the server's order is kept
      expect([for (final p in detail.progress) p.status], [ActivityStatus.inProgress, ActivityStatus.blocked]);
      expect(detail.status, ActivityStatus.blocked);
      expect(detail.activity.title, 'Preparar informe');
    });

    test('M2-07: an unplanned activity has no original planning', () {
      final detail = ActivityDetailModel.fromJson({
        'actividad': {..._activityJson, 'origen': 'no_planificada'},
        'planificacion_original': null,
        'continuaciones_planificadas': <dynamic>[],
        'avances': <dynamic>[],
        'estado_actual': 'Pendiente',
      }).toEntity();
      expect(detail.originalPlanning, isNull);
      expect(detail.activity.origin, ActivityOrigin.unplanned);
      expect(detail.progress, isEmpty);
    });

    test('M2-07: the reason of an error mark is kept', () {
      final activity = ActivityModel.fromJson({
        ..._activityJson,
        'marca_error': {'motivo': 'duplicada', 'marcada_en': '2026-11-06T16:00:00Z'},
      }).toEntity();
      expect(activity.marked, isTrue);
      expect(activity.markReason, 'duplicada');
    });

    test('M2-08: a page of the list with its cursor, and the last page without one', () {
      final page = ActivityListModel.fromJson({
        'elementos': [
          {'id': 'a-2', 'titulo': 'Segunda', 'origen': 'no_planificada', 'estado_actual': 'Completada'},
          {'id': 'a-1', 'titulo': 'Primera', 'origen': 'planificada', 'estado_actual': 'Pendiente'},
        ],
        'siguiente': 'cursor-opaco',
      }).toEntity();
      expect(page.items.map((i) => i.title), ['Segunda', 'Primera']);
      expect(page.items.first.origin, ActivityOrigin.unplanned);
      expect(page.items.first.status, ActivityStatus.completed);
      expect(page.next, 'cursor-opaco');
      final last = ActivityListModel.fromJson({'elementos': <dynamic>[], 'siguiente': null}).toEntity();
      expect(last.items, isEmpty);
      expect(last.next, isNull);
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

  group('progress over the wire (M2-05)', () {
    Map<String, dynamic> body({String status = 'En progreso'}) => {
      'avance': {..._progressJson, 'estado': status},
      'actividad': {..._activityJson, 'estado_actual': status},
      'bitacora_creada': false,
    };

    test('posts to the activity, with the contract fields, the CSRF token and the idempotency key', () async {
      final adapter = FakeAdapter((_) => jsonBody(body(), status: 201));
      final client = _client(adapter)..csrf = 'csrf-9';
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(client));
      final result = await repo.registerProgress(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.inProgress,
        description: 'Avancé con el informe',
        key: 'key-7',
      );
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/actividades/a-1/avances');
      expect(request.headers['Idempotency-Key'], 'key-7');
      expect(request.headers['X-CSRF-Token'], 'csrf-9');
      expect(request.data, {
        'fecha_laboral': '2026-11-05',
        'estado': 'En progreso',
        'descripcion': 'Avancé con el informe',
      });
      expect(result.activity.status, ActivityStatus.inProgress);
    });

    test('the reason travels only with the blocked status', () async {
      final adapter = FakeAdapter((_) => jsonBody(body(status: 'Bloqueada'), status: 201));
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      await repo.registerProgress(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.blocked,
        description: 'Me detuve',
        blockReason: 'Falta el acceso',
        key: 'k-1',
      );
      expect(adapter.requests.single.data['motivo_bloqueo'], 'Falta el acceso');
      // A leftover reason with any other status is never sent
      await repo.registerProgress(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.inProgress,
        description: 'Sigo',
        blockReason: 'sobrante',
        key: 'k-2',
      );
      expect(adapter.requests.last.data.containsKey('motivo_bloqueo'), isFalse);
    });

    test('never sends fields outside the contract (no activity id in the body, no owner, no sequence)', () async {
      final adapter = FakeAdapter((_) => jsonBody(body(), status: 201));
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      await repo.registerProgress(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.inProgress,
        description: 'x',
        key: 'k',
      );
      expect((adapter.requests.single.data as Map).keys.toSet(), {'fecha_laboral', 'estado', 'descripcion'});
    });

    test('server rejections reach the caller with their code', () async {
      for (final (code, status) in [
        ('ACTIVIDAD_COMPLETADA', 409),
        ('MOTIVO_BLOQUEO_OBLIGATORIO', 422),
        ('FECHA_FUTURA_NO_PERMITIDA', 422),
        ('BITACORA_CERRADA', 409),
        ('RECURSO_NO_DISPONIBLE', 404),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
        await expectLater(
          repo.registerProgress(
            activityId: 'a-1',
            date: DateTime.utc(2026, 11, 5),
            status: ActivityStatus.inProgress,
            description: 'x',
            key: 'k',
          ),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });
  });

  group('activity detail and list over the wire (M2-07, M2-08)', () {
    Map<String, dynamic> pageBody({String? next}) => {
      'elementos': [
        {'id': 'a-1', 'titulo': 'Preparar informe', 'origen': 'planificada', 'estado_actual': 'Pendiente'},
      ],
      'siguiente': next,
    };

    test('the detail is requested by id and read-only', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'actividad': _activityJson,
          'planificacion_original': _planningJson,
          'continuaciones_planificadas': <dynamic>[],
          'avances': [_progressJson],
          'estado_actual': 'Bloqueada',
        }),
      );
      final client = _client(adapter)..csrf = 'csrf-1';
      final detail = await LogbookRepositoryImpl(LogbookRemoteDataSource(client)).getActivity('a-1');
      final request = adapter.requests.single;
      expect(request.method, 'GET');
      expect(request.path, '/api/v1/mi/actividades/a-1');
      expect(request.headers.containsKey('Idempotency-Key'), isFalse);
      expect(request.headers.containsKey('X-CSRF-Token'), isFalse); // a read sends no token
      expect(detail.progress.single.blockReason, 'Falta el acceso');
    });

    test('the list without a filter sends no parameters', () async {
      final adapter = FakeAdapter((_) => jsonBody(pageBody()));
      final page = await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).listActivities();
      final request = adapter.requests.single;
      expect(request.method, 'GET');
      expect(request.path, '/api/v1/mi/actividades');
      expect(request.queryParameters, isEmpty);
      expect(page.items.single.id, 'a-1');
    });

    test('statuses travel as repeated estado parameters with the contract names', () async {
      final adapter = FakeAdapter((_) => jsonBody(pageBody()));
      await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).listActivities(
        statuses: [ActivityStatus.pending, ActivityStatus.blocked],
      );
      final request = adapter.requests.single;
      expect(request.queryParameters, {
        'estado': ['Pendiente', 'Bloqueada'],
      });
      expect(request.uri.toString(), contains('estado=Pendiente&estado=Bloqueada'));
    });

    test('the page size and the cursor travel with the contract names, and nothing else', () async {
      final adapter = FakeAdapter((_) => jsonBody(pageBody()));
      await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).listActivities(
        statuses: [ActivityStatus.completed],
        limit: 10,
        cursor: 'abc_DEF-123',
      );
      expect(adapter.requests.single.queryParameters, {
        'estado': ['Completada'],
        'limite': 10,
        'continuar_desde': 'abc_DEF-123',
      });
    });

    test('the next-page cursor is passed through untouched', () async {
      final adapter = FakeAdapter((_) => jsonBody(pageBody(next: 'eyJjIjoiMjAyNiJ9')));
      final page = await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).listActivities();
      expect(page.next, 'eyJjIjoiMjAyNiJ9');
    });

    test('rejections reach the caller with their code', () async {
      for (final (call, code, status) in <(Future<Object> Function(LogbookRepositoryImpl), String, int)>[
        ((r) => r.getActivity('a-1'), 'RECURSO_NO_DISPONIBLE', 404),
        ((r) => r.getActivity('x'), 'SOLICITUD_INVALIDA', 400),
        ((r) => r.listActivities(), 'SOLICITUD_INVALIDA', 400),
        ((r) => r.listActivities(), 'ACCESO_DESACTIVADO', 403),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
        await expectLater(call(repo), throwsA(isA<ApiError>().having((e) => e.code, 'code', code)), reason: code);
      }
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
