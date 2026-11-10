import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the M3-04 contract defines (docs/api/m3-seguimiento-auditoria.md).
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
const _progressJson = {
  'id': 'av-9',
  'actividad_id': 'a-1',
  'fecha_laboral': '2026-11-05',
  'estado': 'En progreso',
  'descripcion': 'Retomo las cifras',
  'motivo_bloqueo': null,
  'es_reactivacion': true,
  'registrado_en': '2026-11-06T16:00:00Z',
};

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

LogbookRepositoryImpl _repo(FakeAdapter adapter) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)..csrf = 'csrf-4'));

Map<String, dynamic> _body({String status = 'En progreso', bool created = false, Map<String, dynamic>? progress}) => {
  'avance': {..._progressJson, 'estado': status, ...?progress},
  'actividad': {..._activityJson, 'estado_actual': status},
  'bitacora_creada': created,
};

void main() {
  group('M3-04 over the wire', () {
    test('posts to the reactivation resource of THAT activity with the token and the key', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(created: true), status: 201));
      final result = await _repo(adapter).reactivateActivity(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.inProgress,
        description: 'Retomo las cifras',
        key: 'key-7',
      );
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/actividades/a-1/reactivacion');
      expect(request.headers['Idempotency-Key'], 'key-7');
      expect(request.headers['X-CSRF-Token'], 'csrf-4');
      expect(request.data, {'fecha_laboral': '2026-11-05', 'estado': 'En progreso', 'descripcion': 'Retomo las cifras'});
      expect(result.progress.isReactivation, isTrue);
      expect(result.progress.date, DateTime.utc(2026, 11, 5));
      expect(result.activity.id, 'a-1'); // the SAME activity: nothing new is created
      expect(result.activity.status, ActivityStatus.inProgress);
      expect(result.logbookCreated, isTrue);
    });

    test('the block reason travels only with Bloqueada', () async {
      final blocked = FakeAdapter((_) => jsonBody(_body(status: 'Bloqueada'), status: 201));
      await _repo(blocked).reactivateActivity(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.blocked,
        description: 'Retomo',
        blockReason: 'Falta el acceso',
        key: 'k',
      );
      expect(blocked.requests.single.data, {
        'fecha_laboral': '2026-11-05',
        'estado': 'Bloqueada',
        'descripcion': 'Retomo',
        'motivo_bloqueo': 'Falta el acceso',
      });

      final other = FakeAdapter((_) => jsonBody(_body(status: 'Pendiente'), status: 201));
      await _repo(other).reactivateActivity(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.pending,
        description: 'Retomo',
        blockReason: 'sobra', // a stale reason is never sent for another status
        key: 'k',
      );
      expect((other.requests.single.data as Map).containsKey('motivo_bloqueo'), isFalse);
    });

    test('never sends a title, an owner, an origin or a flag: the server decides what it is', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(), status: 201));
      await _repo(adapter).reactivateActivity(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.pending,
        description: 'D',
        key: 'k',
      );
      expect((adapter.requests.single.data as Map).keys.toSet(), {'fecha_laboral', 'estado', 'descripcion'});
    });

    test('the response gives the entry flagged as a reactivation and the recalculated status', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(status: 'Pendiente'), status: 201));
      final result = await _repo(adapter).reactivateActivity(
        activityId: 'a-1',
        date: DateTime.utc(2026, 11, 5),
        status: ActivityStatus.pending,
        description: 'D',
        key: 'k',
      );
      expect(result.progress.isReactivation, isTrue);
      expect(result.progress.status, ActivityStatus.pending);
      expect(result.activity.status, ActivityStatus.pending);
      expect(result.logbookCreated, isFalse);
    });

    test('server rejections reach the caller with their code', () async {
      for (final (code, status) in [
        ('ACTIVIDAD_NO_COMPLETADA', 409),
        ('ACTIVIDAD_MARCADA_POR_ERROR', 409),
        ('SECUENCIA_INVALIDA', 409),
        ('BITACORA_CERRADA', 409),
        ('FECHA_FUTURA_NO_PERMITIDA', 422),
        ('ESTADO_INVALIDO', 422),
        ('DESCRIPCION_OBLIGATORIA', 422),
        ('MOTIVO_BLOQUEO_OBLIGATORIO', 422),
        ('RECURSO_NO_DISPONIBLE', 404),
        ('CLAVE_IDEMPOTENCIA_REUTILIZADA', 422),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        await expectLater(
          _repo(adapter).reactivateActivity(
            activityId: 'a-1',
            date: DateTime.utc(2026, 11, 5),
            status: ActivityStatus.pending,
            description: 'D',
            key: 'k',
          ),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });

    test('the new rejections have their own message in Spanish, and none shows the server text', () {
      for (final code in ['ACTIVIDAD_NO_COMPLETADA', 'SECUENCIA_INVALIDA']) {
        final message = errorMessage(ApiError(code: code, message: 'texto del servidor', status: 409));
        expect(message, isNot(contains('texto del servidor')), reason: code);
        expect(message, isNot('Se produjo un error inesperado. Inténtalo de nuevo.'), reason: code);
      }
    });
  });
}
