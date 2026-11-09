import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/models/logbook_models.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';

import '../helpers/fakes.dart';

// Payload with the shape the M2-02 contract defines (docs/api/m2-bitacoras.md and conventions 7).
Map<String, dynamic> _body({String summary = 'Avancé con el informe', bool created = false}) => {
  'bitacora': {
    'id': 'b-1',
    'persona_id': 'p-1',
    'fecha_laboral': '2026-11-06',
    'clase_jornada': 'actual',
    'estado': 'abierta',
    'resumen': summary,
    'cerrada_en': null,
    'creada_en': '2026-11-06T15:30:00Z',
    'modificada_en': '2026-11-06T17:45:00Z',
  },
  'bitacora_creada': created,
};

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

void main() {
  group('M2-02 over the wire', () {
    test('replaces the summary with a PUT to the day, with the CSRF token and NO idempotency key', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      final client = _client(adapter)..csrf = 'csrf-3';
      final result = await LogbookRepositoryImpl(LogbookRemoteDataSource(client)).saveSummary(
        date: DateTime.utc(2026, 11, 6),
        summary: 'Avancé con el informe',
      );
      final request = adapter.requests.single;
      expect(request.method, 'PUT');
      expect(request.path, '/api/v1/mi/bitacoras/2026-11-06/resumen');
      expect(request.headers['X-CSRF-Token'], 'csrf-3');
      expect(request.headers.containsKey('Idempotency-Key'), isFalse); // a replacement needs none
      expect(request.data, {'resumen': 'Avancé con el informe'});
      expect(result.logbook.summary, 'Avancé con el informe');
      expect(result.logbookCreated, isFalse);
    });

    test('the text goes exactly as typed: no trimming, no changes', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      const text = '  Primera línea\n\tSegunda <b>línea</b> con \'comillas\' y ✓  ';
      await repo.saveSummary(date: DateTime.utc(2026, 11, 6), summary: text);
      expect(adapter.requests.single.data, {'resumen': text});
    });

    test('an empty summary is sent as an empty string, never omitted', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(summary: '')));
      final result = await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).saveSummary(
        date: DateTime.utc(2026, 11, 6),
        summary: '',
      );
      expect(adapter.requests.single.data, {'resumen': ''});
      expect(result.logbook.summary, isEmpty);
    });

    test('sends nothing but the summary: no state, no dates, no owner', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).saveSummary(
        date: DateTime.utc(2026, 11, 6),
        summary: 'x',
      );
      expect((adapter.requests.single.data as Map).keys.toSet(), {'resumen'});
    });

    test('the response gives the logbook as the server holds it and whether it was created', () {
      final result = SummaryResultModel.fromJson(_body(summary: 'Nuevo', created: true)).toEntity();
      expect(result.logbook.summary, 'Nuevo');
      expect(result.logbook.updatedAt, DateTime.utc(2026, 11, 6, 17, 45));
      expect(result.logbook.createdAt, DateTime.utc(2026, 11, 6, 15, 30));
      expect(result.logbook.closed, isFalse);
      expect(result.logbookCreated, isTrue);
    });

    test('server rejections reach the caller with their code', () async {
      for (final (code, status) in [
        ('TEXTO_DEMASIADO_LARGO', 422),
        ('BITACORA_CERRADA', 409),
        ('FECHA_NO_CUBIERTA', 422),
        ('SOLICITUD_INVALIDA', 400),
        ('ACCESO_DESACTIVADO', 403),
        ('SIN_PERTENENCIA_VIGENTE', 403),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
        await expectLater(
          repo.saveSummary(date: DateTime.utc(2026, 11, 6), summary: 'x'),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });

    test('a text that is too long is explained with the maximum the server reports', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'codigo': 'TEXTO_DEMASIADO_LARGO',
          'mensaje': 'x',
          'detalles': [
            {'campo': 'resumen', 'maximo': 8000},
          ],
        }, status: 422),
      );
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      final error = await repo
          .saveSummary(date: DateTime.utc(2026, 11, 6), summary: 'x')
          .then<ApiError?>((_) => null, onError: (Object e) => e as ApiError);
      expect(errorMessage(error!), contains('8000'));
    });
  });
}
