import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the M3-03 contract defines (docs/api/m3-seguimiento-auditoria.md).
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
  'estado': 'Bloqueada',
  'descripcion': 'Texto corregido',
  'motivo_bloqueo': 'Falta el acceso',
  'es_reactivacion': false,
  'registrado_en': '2026-11-05T16:00:00Z',
  'modificado_en': '2026-11-06T09:30:00Z',
};

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

LogbookRepositoryImpl _repo(FakeAdapter adapter) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)..csrf = 'csrf-5'));

Map<String, dynamic> _body({bool changed = true}) => {
  'avance': _progressJson,
  'actividad': {..._activityJson, 'estado_actual': 'Bloqueada'},
  'estado_actual_cambio': changed,
};

void main() {
  group('M3-03 over the wire', () {
    test('patches THAT entry with the token and the key, sending only the corrected fields', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      final result = await _repo(adapter).correctProgress(
        progressId: 'av-9',
        correction: const ProgressCorrection(status: ActivityStatus.blocked, blockReason: 'Falta el acceso'),
        key: 'key-8',
      );
      final request = adapter.requests.single;
      expect(request.method, 'PATCH');
      expect(request.path, '/api/v1/mi/avances/av-9');
      expect(request.headers['Idempotency-Key'], 'key-8');
      expect(request.headers['X-CSRF-Token'], 'csrf-5');
      expect(request.data, {'estado': 'Bloqueada', 'motivo_bloqueo': 'Falta el acceso'});
      expect(result.progress.id, 'av-9');
      expect(result.progress.status, ActivityStatus.blocked);
      expect(result.progress.blockReason, 'Falta el acceso');
      expect(result.activity.status, ActivityStatus.blocked);
      expect(result.currentStatusChanged, isTrue);
    });

    test('never sends the work date, an identifier, the reactivation flag or a timestamp', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      await _repo(adapter).correctProgress(
        progressId: 'av-9',
        correction: const ProgressCorrection(
          status: ActivityStatus.blocked,
          description: 'Otro texto',
          blockReason: 'Motivo',
        ),
        key: 'k',
      );
      final keys = (adapter.requests.single.data as Map).keys.toSet();
      expect(keys, {'estado', 'descripcion', 'motivo_bloqueo'});
      expect(keys.intersection({'fecha_laboral', 'id', 'actividad_id', 'es_reactivacion', 'registrado_en', 'modificado_en'}), isEmpty);
    });

    test('only the description travels when only the description changed', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(changed: false)));
      final result = await _repo(adapter).correctProgress(
        progressId: 'av-9',
        correction: const ProgressCorrection(description: 'Solo el texto'),
        key: 'k',
      );
      expect(adapter.requests.single.data, {'descripcion': 'Solo el texto'});
      expect(result.currentStatusChanged, isFalse);
    });

    test('the moment of the correction is read, and an entry corrected after its record says so', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      final result = await _repo(adapter).correctProgress(
        progressId: 'av-9',
        correction: const ProgressCorrection(description: 'x'),
        key: 'k',
      );
      expect(result.progress.modifiedAt, DateTime.utc(2026, 11, 6, 9, 30));
      expect(result.progress.corrected, isTrue);
    });

    test('an entry whose modification equals its record is not corrected (CA-62)', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          ..._body(),
          'avance': {..._progressJson, 'modificado_en': '2026-11-05T16:00:00Z'},
        }),
      );
      final result = await _repo(adapter).correctProgress(
        progressId: 'av-9',
        correction: const ProgressCorrection(description: 'x'),
        key: 'k',
      );
      expect(result.progress.corrected, isFalse);
    });

    test('a payload without modificado_en still parses (the entry is just not corrected)', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          ..._body(),
          'avance': Map.of(_progressJson)..remove('modificado_en'),
        }),
      );
      final result = await _repo(adapter).correctProgress(
        progressId: 'av-9',
        correction: const ProgressCorrection(description: 'x'),
        key: 'k',
      );
      expect(result.progress.modifiedAt, isNull);
      expect(result.progress.corrected, isFalse);
    });

    test('the server errors keep their code and details so the screen can explain each one', () async {
      for (final code in [
        'SECUENCIA_INVALIDA',
        'ACTIVIDAD_MARCADA_POR_ERROR',
        'BITACORA_CERRADA',
        'MOTIVO_BLOQUEO_OBLIGATORIO',
        'DESCRIPCION_OBLIGATORIA',
        'ESTADO_INVALIDO',
      ]) {
        final adapter = FakeAdapter(
          (_) => jsonBody({
            'codigo': code,
            'mensaje': 'x',
            'detalles': [
              {'campo': 'estado', 'motivo': 'avance_tras_finalizacion_sin_reactivacion'},
            ],
          }, status: 409),
        );
        await expectLater(
          _repo(adapter).correctProgress(
            progressId: 'av-9',
            correction: const ProgressCorrection(description: 'x'),
            key: 'k',
          ),
          throwsA(
            isA<ApiError>()
                .having((e) => e.code, 'code', code)
                .having((e) => e.details.first['motivo'], 'motivo', 'avance_tras_finalizacion_sin_reactivacion'),
          ),
          reason: code,
        );
      }
    });
  });

  group('messages', () {
    test('the existing messages cover the rejections of a correction, with no server text', () {
      for (final code in ['ACTIVIDAD_MARCADA_POR_ERROR', 'BITACORA_CERRADA', 'MOTIVO_BLOQUEO_OBLIGATORIO', 'DESCRIPCION_OBLIGATORIA']) {
        final text = errorMessage(ApiError(code: code, message: 'texto del servidor', status: 409));
        expect(text, isNotEmpty, reason: code);
        expect(text, isNot(contains('texto del servidor')), reason: code);
      }
    });
  });
}
