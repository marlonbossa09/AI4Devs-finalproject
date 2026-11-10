import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/audit_entities.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the M3-07 contract defines (docs/api/m3-seguimiento-auditoria.md).
Map<String, dynamic> _entry(String id, {String operation = 'correccion', Map<String, dynamic>? extra}) => {
  'id': id,
  'momento': '2026-11-06T15:30:00.250Z',
  'tipo_autor': 'persona',
  'autor_persona_id': 'p-1',
  'operacion': operation,
  'tipo_objeto': 'avance',
  'objeto_id': 'av-9',
  'propietaria_registro_id': 'p-1',
  'fecha_laboral_registro': '2026-11-05',
  'motivo': null,
  'valor_anterior': {
    'avance': {'descripcion': 'Texto'},
  },
  'valor_nuevo': {
    'avance': {'descripcion': 'Otro texto'},
  },
  ...?extra,
};

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

LogbookRepositoryImpl _repo(FakeAdapter adapter) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)..csrf = 'csrf-6'));

void main() {
  group('M3-07 over the wire', () {
    test('asks for the audit of ONE record with the type and the id, and nothing else', () async {
      final adapter = FakeAdapter((_) => jsonBody({'elementos': [], 'siguiente': null}));
      await _repo(adapter).listAudit(type: AuditObjectType.progress, objectId: 'av-9');
      final request = adapter.requests.single;
      expect(request.method, 'GET');
      expect(request.path, '/api/v1/auditoria');
      expect(request.queryParameters, {'tipo_objeto': 'avance', 'objeto_id': 'av-9'});
      expect(request.data, isNull); // a read: no body, no idempotency key
      expect(request.headers.containsKey('Idempotency-Key'), isFalse);
    });

    test('each kind of record travels with its own name, without accents', () async {
      final wire = {
        AuditObjectType.logbook: 'bitacora',
        AuditObjectType.activity: 'actividad',
        AuditObjectType.progress: 'avance',
      };
      for (final entry in wire.entries) {
        final adapter = FakeAdapter((_) => jsonBody({'elementos': [], 'siguiente': null}));
        await _repo(adapter).listAudit(type: entry.key, objectId: 'x');
        expect(adapter.requests.single.queryParameters['tipo_objeto'], entry.value, reason: entry.key.name);
      }
    });

    test('the limit and the cursor travel only when given, and the cursor is sent as the server issued it', () async {
      final adapter = FakeAdapter((_) => jsonBody({'elementos': [], 'siguiente': null}));
      await _repo(adapter).listAudit(type: AuditObjectType.activity, objectId: 'a-1', limit: 5, cursor: 'eyJtIjoieCJ9');
      expect(adapter.requests.single.queryParameters, {
        'tipo_objeto': 'actividad',
        'objeto_id': 'a-1',
        'limite': 5,
        'continuar_desde': 'eyJtIjoieCJ9',
      });
    });

    test('never sends a person, a team, a text or an operation filter: there is no global audit', () async {
      final adapter = FakeAdapter((_) => jsonBody({'elementos': [], 'siguiente': null}));
      await _repo(adapter).listAudit(type: AuditObjectType.logbook, objectId: 'b-1');
      final keys = adapter.requests.single.queryParameters.keys.toSet();
      expect(keys.difference({'tipo_objeto', 'objeto_id', 'limite', 'continuar_desde'}), isEmpty);
    });

    test('reads the entries in the order the server sends them, with the cursor of the next page', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'elementos': [_entry('e-1'), _entry('e-2', operation: 'marca_error')],
          'siguiente': 'cursor-2',
        }),
      );
      final page = await _repo(adapter).listAudit(type: AuditObjectType.progress, objectId: 'av-9');
      expect(page.items.map((e) => e.id), ['e-1', 'e-2']);
      expect(page.next, 'cursor-2');
    });

    test('the last page has no cursor', () async {
      final adapter = FakeAdapter((_) => jsonBody({'elementos': [_entry('e-1')], 'siguiente': null}));
      expect((await _repo(adapter).listAudit(type: AuditObjectType.progress, objectId: 'av-9')).next, isNull);
    });

    test('an entry carries its moment, author, operation, work date, reason and before/after values', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'elementos': [
            _entry('e-1', extra: {'motivo': 'Faltaba una cifra'}),
          ],
          'siguiente': null,
        }),
      );
      final entry = (await _repo(adapter).listAudit(type: AuditObjectType.progress, objectId: 'av-9')).items.single;
      expect(entry.moment, DateTime.utc(2026, 11, 6, 15, 30, 0, 250));
      expect(entry.authorId, 'p-1');
      expect(entry.operation, AuditOperation.correction);
      expect(entry.operationName, 'correccion');
      expect(entry.workDate, DateTime.utc(2026, 11, 5));
      expect(entry.reason, 'Faltaba una cifra');
      expect(entry.previous, {
        'avance': {'descripcion': 'Texto'},
      });
      expect(entry.next, {
        'avance': {'descripcion': 'Otro texto'},
      });
    });

    test('every operation of the contract is recognized; an unknown one is kept as such', () async {
      const names = {
        'cierre': AuditOperation.closing,
        'reapertura': AuditOperation.reopening,
        'correccion': AuditOperation.correction,
        'modificacion_jornada_pasada': AuditOperation.pastDayChange,
        'reactivacion': AuditOperation.reactivation,
        'marca_error': AuditOperation.errorMark,
        'reversion_marca': AuditOperation.markReversal,
        'algo_nuevo': AuditOperation.other,
      };
      final adapter = FakeAdapter((_) => jsonBody({'elementos': [for (final n in names.keys) _entry(n, operation: n)], 'siguiente': null}));
      final page = await _repo(adapter).listAudit(type: AuditObjectType.progress, objectId: 'av-9');
      expect(page.items.map((e) => e.operation).toList(), names.values.toList());
      expect(page.items.last.operationName, 'algo_nuevo');
    });

    test('an entry without values, reason or work date still parses', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'elementos': [
            _entry('e-1', extra: {'valor_anterior': null, 'valor_nuevo': null, 'fecha_laboral_registro': null, 'autor_persona_id': null}),
          ],
          'siguiente': null,
        }),
      );
      final entry = (await _repo(adapter).listAudit(type: AuditObjectType.progress, objectId: 'av-9')).items.single;
      expect((entry.previous, entry.next, entry.workDate, entry.reason, entry.authorId), (null, null, null, null, null));
    });

    test('an unavailable record keeps its code and reveals nothing else', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({'codigo': 'RECURSO_NO_DISPONIBLE', 'mensaje': 'El recurso solicitado no está disponible', 'detalles': []}, status: 404),
      );
      await expectLater(
        _repo(adapter).listAudit(type: AuditObjectType.activity, objectId: 'ajena'),
        throwsA(isA<ApiError>().having((e) => e.code, 'code', 'RECURSO_NO_DISPONIBLE').having((e) => e.details, 'details', isEmpty)),
      );
    });

    test('the other rejections keep their code', () async {
      for (final (code, status) in [('SOLICITUD_INVALIDA', 400), ('NO_IDENTIFICADA', 401), ('ACCESO_DESACTIVADO', 403)]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        await expectLater(
          _repo(adapter).listAudit(type: AuditObjectType.activity, objectId: 'a'),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });
  });
}
