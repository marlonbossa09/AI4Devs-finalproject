import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/models/logbook_models.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/continuation_rules.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the M2-04 contract defines (docs/api/m2-bitacoras.md).
const _activityJson = {
  'id': 'a-1',
  'propietaria_id': 'p-1',
  'titulo': 'Preparar informe',
  'origen': 'planificada',
  'estado_actual': 'En progreso',
  'marca_error': null,
  'fecha_laboral_origen': '2026-11-06',
  'creada_en': '2026-11-06T09:00:00Z',
};
const _planningJson = {
  'id': 'pl-2',
  'actividad_id': 'a-1',
  'fecha_laboral': '2026-11-09',
  'tipo': 'continuacion',
  'clase': 'vigente',
  'descripcion': 'Cerrar las cifras',
  'registrada_en': '2026-11-06T16:00:00Z',
};

final _today = DateTime.utc(2026, 11, 6);

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

Map<String, dynamic> _body({String status = 'En progreso', bool created = true}) => {
  'planificacion': _planningJson,
  'actividad': {..._activityJson, 'estado_actual': status},
  'bitacora_creada': created,
};

LogbookRepositoryImpl _repo(FakeAdapter adapter, {String csrf = 'csrf-4'}) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)..csrf = csrf));

void main() {
  group('validateContinuation (RN-76)', () {
    test('a date after today is accepted', () {
      expect(validateContinuation(date: DateTime.utc(2026, 11, 7), today: _today).isEmpty, isTrue);
      expect(validateContinuation(date: DateTime.utc(2030, 1, 1), today: _today).isEmpty, isTrue);
    });

    test('today and the past are rejected: they are for progress, not for planning', () {
      for (final date in [_today, DateTime.utc(2026, 11, 5), DateTime.utc(2020, 1, 1)]) {
        expect(
          validateContinuation(date: date, today: _today).date,
          'Elige una fecha posterior a hoy.',
          reason: date.toString(),
        );
      }
    });
  });

  group('canPlanContinuation (RN-78)', () {
    test('Pendiente, En progreso and Bloqueada can be continued', () {
      for (final status in [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked]) {
        expect(canPlanContinuation(status: status, marked: false), isTrue, reason: status.name);
      }
    });

    test('a Completada activity cannot, until it is reactivated', () {
      expect(canPlanContinuation(status: ActivityStatus.completed, marked: false), isFalse);
    });

    test('an activity marked as an error never can, whatever its status', () {
      for (final status in ActivityStatus.values) {
        expect(canPlanContinuation(status: status, marked: true), isFalse, reason: status.name);
      }
    });
  });

  group('M2-04 over the wire', () {
    test('posts to the continuations resource of THAT activity with the token and the key', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(), status: 201));
      final result = await _repo(adapter).planContinuation(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 9),
        description: 'Cerrar las cifras',
        key: 'key-7',
      );
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/actividades/a-1/continuaciones-planificadas');
      expect(request.headers['Idempotency-Key'], 'key-7');
      expect(request.headers['X-CSRF-Token'], 'csrf-4');
      expect(request.data, {'fecha_laboral': '2026-11-09', 'descripcion': 'Cerrar las cifras'});
      expect(result.planning.type, PlanningType.continuation);
      expect(result.planning.date, DateTime.utc(2026, 11, 9));
      expect(result.planning.description, 'Cerrar las cifras');
      expect(result.logbookCreated, isTrue);
    });

    test('the description is optional: without one the field is not sent', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(), status: 201));
      await _repo(adapter).planContinuation(activityId: 'a-1', date: DateTime.utc(2026, 11, 9), key: 'k');
      expect(adapter.requests.single.data, {'fecha_laboral': '2026-11-09'});
    });

    test('never sends a status, a title, an origin or an owner: it is a planning, not progress', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(), status: 201));
      await _repo(adapter).planContinuation(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 9),
        description: 'D',
        key: 'k',
      );
      expect((adapter.requests.single.data as Map).keys.toSet(), {'fecha_laboral', 'descripcion'});
    });

    test('the response keeps the activity as it was: the same id and the same status', () {
      final result = ContinuationResultModel.fromJson(_body(status: 'Bloqueada', created: false)).toEntity();
      expect(result.activity.id, 'a-1');
      expect(result.activity.status, ActivityStatus.blocked); // planning it did not change the status
      expect(result.planning.activityId, 'a-1');
      expect(result.logbookCreated, isFalse);
    });

    test('server rejections reach the caller with their code', () async {
      for (final (code, status) in [
        ('FECHA_NO_FUTURA', 422),
        ('FECHA_NO_CUBIERTA', 422),
        ('ACTIVIDAD_COMPLETADA', 409),
        ('ACTIVIDAD_MARCADA_POR_ERROR', 409),
        ('RECURSO_NO_DISPONIBLE', 404),
        ('TEXTO_DEMASIADO_LARGO', 422),
        ('CLAVE_IDEMPOTENCIA_REUTILIZADA', 422),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        await expectLater(
          _repo(adapter).planContinuation(activityId: 'a-1', date: DateTime.utc(2026, 11, 9), key: 'k'),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });

    test('every rejection has its own message in Spanish, and none reveals protected data', () {
      for (final code in ['FECHA_NO_FUTURA', 'ACTIVIDAD_COMPLETADA', 'ACTIVIDAD_MARCADA_POR_ERROR', 'FECHA_NO_CUBIERTA']) {
        final message = errorMessage(ApiError(code: code, message: 'texto del servidor', status: 409));
        expect(message, isNot(contains('texto del servidor')), reason: code);
        expect(message, isNot('Se produjo un error inesperado. Inténtalo de nuevo.'), reason: code);
      }
    });
  });

  group('LogbookDay tells the original planning and the continuations apart', () {
    final activity = Activity(
      id: 'a-1',
      userId: 'p1',
      title: 'Preparar informe',
      origin: ActivityOrigin.planned,
      status: ActivityStatus.inProgress,
      date: DateTime.utc(2026, 11, 6),
      createdAt: DateTime.utc(2026, 11, 6, 9),
    );
    Planning planning(String id, PlanningType type, String activityId) => Planning(
      id: id,
      activityId: activityId,
      date: DateTime.utc(2026, 11, 9),
      type: type,
      description: id,
      createdAt: DateTime.utc(2026, 11, 6, 16),
    );
    final day = LogbookDay(
      logbook: Logbook(
        id: 'b1',
        userId: 'p1',
        date: DateTime.utc(2026, 11, 9),
        dateType: DateType.future,
        closed: false,
        summary: '',
        createdAt: DateTime.utc(2026, 11, 6),
        updatedAt: DateTime.utc(2026, 11, 6),
      ),
      plannings: [
        planning('cont-1', PlanningType.continuation, 'a-1'),
        planning('orig-1', PlanningType.original, 'a-1'),
        planning('cont-2', PlanningType.continuation, 'a-1'),
        planning('cont-other', PlanningType.continuation, 'a-2'),
      ],
      activities: [activity],
    );

    test('planningOf returns only the ORIGINAL planning, even when a continuation comes first', () {
      expect(day.planningOf(activity)?.id, 'orig-1');
    });

    test('planningOf is null when the day only has continuations of the activity', () {
      final onlyContinuations = LogbookDay(
        logbook: day.logbook,
        plannings: [planning('cont-1', PlanningType.continuation, 'a-1')],
        activities: [activity],
      );
      expect(onlyContinuations.planningOf(activity), isNull);
    });

    test('continuationsOf returns only the continuations of THAT activity, in order', () {
      expect(day.continuationsOf(activity).map((p) => p.id), ['cont-1', 'cont-2']);
    });
  });
}
