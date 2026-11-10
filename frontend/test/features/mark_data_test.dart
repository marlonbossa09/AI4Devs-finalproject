import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the M3-05 and M3-06 contracts define (docs/api/m3-seguimiento-auditoria.md).
const _activityJson = {
  'id': 'a-1',
  'propietaria_id': 'p-1',
  'titulo': 'Preparar informe',
  'origen': 'planificada',
  'estado_actual': 'En progreso',
  'marca_error': null,
  'fecha_laboral_origen': '2026-11-02',
  'creada_en': '2026-11-02T09:00:00Z',
};

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

LogbookRepositoryImpl _repo(FakeAdapter adapter) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)..csrf = 'csrf-9'));

Map<String, dynamic> _marked({String reason = 'Se creó dos veces'}) => {
  'actividad': {
    ..._activityJson,
    'marca_error': {'motivo': reason, 'marcada_en': '2026-11-06T16:00:00Z'},
  },
};

void main() {
  group('M3-05 over the wire', () {
    test('posts the reason to the error-mark resource of THAT activity, with the token and the key', () async {
      final adapter = FakeAdapter((_) => jsonBody(_marked()));
      final result = await _repo(adapter).markActivityAsError(activityId: 'a-1', reason: 'Se creó dos veces', key: 'key-3');
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/actividades/a-1/marca-error');
      expect(request.headers['Idempotency-Key'], 'key-3');
      expect(request.headers['X-CSRF-Token'], 'csrf-9');
      expect(request.data, {'motivo': 'Se creó dos veces'});
      expect(result.activity.id, 'a-1');
      expect(result.activity.marked, isTrue);
      expect(result.activity.markReason, 'Se creó dos veces');
    });

    test('the status does not change: a mark is not a fifth status', () async {
      final adapter = FakeAdapter((_) => jsonBody(_marked()));
      final result = await _repo(adapter).markActivityAsError(activityId: 'a-1', reason: 'x', key: 'k');
      expect(result.activity.status.name, 'inProgress');
    });

    test('sends nothing but the reason: no status, title, owner or date', () async {
      final adapter = FakeAdapter((_) => jsonBody(_marked()));
      await _repo(adapter).markActivityAsError(activityId: 'a-1', reason: 'x', key: 'k');
      expect((adapter.requests.single.data as Map).keys.toSet(), {'motivo'});
    });

    test('the server errors keep their code, so the screen can explain each one', () async {
      for (final code in ['MOTIVO_OBLIGATORIO', 'MARCA_NO_PROCEDE', 'MARCA_INVALIDARIA_CIERRE', 'ACTIVIDAD_MARCADA_POR_ERROR']) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: 409));
        await expectLater(
          _repo(adapter).markActivityAsError(activityId: 'a-1', reason: 'x', key: 'k'),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });
  });

  group('M3-06 over the wire', () {
    test('posts to the reversion resource of THAT activity with no body, the token and the key', () async {
      final adapter = FakeAdapter((_) => jsonBody({'actividad': _activityJson}));
      final result = await _repo(adapter).revertActivityMark(activityId: 'a-1', key: 'key-4');
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/actividades/a-1/marca-error/reversion');
      expect(request.headers['Idempotency-Key'], 'key-4');
      expect(request.headers['X-CSRF-Token'], 'csrf-9');
      expect(request.data, isNull); // no rule asks for a reason to revert
      expect(result.activity.marked, isFalse);
      expect(result.activity.markReason, isNull);
    });

    test('MARCA_NO_VIGENTE keeps its code', () async {
      final adapter = FakeAdapter((_) => jsonBody({'codigo': 'MARCA_NO_VIGENTE', 'mensaje': 'x', 'detalles': []}, status: 409));
      await expectLater(
        _repo(adapter).revertActivityMark(activityId: 'a-1', key: 'k'),
        throwsA(isA<ApiError>().having((e) => e.code, 'code', 'MARCA_NO_VIGENTE')),
      );
    });
  });

  group('the messages explain each rejection in Spanish, with no server text', () {
    String message(String code) => errorMessage(ApiError(code: code, message: 'texto del servidor', status: 409));

    test('later progress', () {
      expect(message('MARCA_NO_PROCEDE'), contains('avances en jornadas posteriores'));
    });

    test('a closed day would be left without a valid activity: says how to proceed', () {
      final text = message('MARCA_INVALIDARIA_CIERRE');
      expect(text, contains('Reabre esa jornada'));
      expect(text, isNot(contains('texto del servidor')));
    });

    test('no mark in force, already marked', () {
      expect(message('MARCA_NO_VIGENTE'), contains('ya no tiene una marca'));
      expect(message('ACTIVIDAD_MARCADA_POR_ERROR'), contains('marcada como registrada por error'));
    });
  });
}
