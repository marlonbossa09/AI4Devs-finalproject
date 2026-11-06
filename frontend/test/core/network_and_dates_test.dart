import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/core/utils/keys.dart';
import 'package:smartwork/core/utils/dates.dart';

import '../helpers/fakes.dart';

void main() {
  group('work dates', () {
    test('parse and format are inverse and never depend on the time zone', () {
      final date = parseDate('2026-11-06');
      expect(date, DateTime.utc(2026, 11, 6));
      expect(formatDate(date), '2026-11-06');
      expect(formatDate(DateTime.utc(5, 1, 2)), '0005-01-02');
    });

    test('addDays crosses month and year boundaries', () {
      expect(formatDate(addDays(DateTime.utc(2026, 12, 31), 1)), '2027-01-01');
      expect(formatDate(addDays(DateTime.utc(2026, 3, 1), -1)), '2026-02-28');
    });

    test('invalid text is rejected', () {
      expect(() => parseDate('hoy'), throwsFormatException);
    });

    test('long date is in Spanish', () {
      expect(formatLongDate(DateTime.utc(2026, 11, 6)), 'viernes 6 de noviembre de 2026');
      expect(formatTopDate(DateTime.utc(2026, 11, 6)), 'Viernes, 6 de noviembre de 2026');
      expect(formatMonth(DateTime.utc(2026, 11, 6)), 'Noviembre de 2026');
      expect(formatShortDate(DateTime.utc(2026, 11, 6)), '06/11/2026');
    });
  });

  group('idempotency key', () {
    test('is random, opaque and 128-bit hex', () {
      final keys = List.generate(50, (_) => newKey());
      expect(keys.toSet().length, 50);
      expect(keys.every((k) => RegExp(r'^[0-9a-f]{32}$').hasMatch(k)), isTrue);
    });
  });

  group('ApiClient', () {
    late FakeAdapter adapter;
    late ApiClient client;

    setUp(() {
      adapter = FakeAdapter((_) => jsonBody({'ok': true}));
      final dio = Dio(BaseOptions(extra: {'withCredentials': true}))..httpClientAdapter = adapter;
      client = ApiClient(dio: dio);
    });

    test('sends the CSRF token only on requests that modify', () async {
      client.csrf = 'token-abc';
      await client.dio.get<dynamic>('/x');
      await client.dio.post<dynamic>('/x');
      await client.dio.put<dynamic>('/x');
      expect(adapter.requests[0].headers.containsKey('X-CSRF-Token'), isFalse);
      expect(adapter.requests[1].headers['X-CSRF-Token'], 'token-abc');
      expect(adapter.requests[2].headers['X-CSRF-Token'], 'token-abc');
    });

    test('sends no token when there is no session', () async {
      await client.dio.post<dynamic>('/x');
      expect(adapter.requests.single.headers.containsKey('X-CSRF-Token'), isFalse);
    });

    test('the idempotency key travels as the Idempotency-Key header', () async {
      await client.dio.post<dynamic>('/x', options: client.withKey('k-1'));
      expect(adapter.requests.single.headers['Idempotency-Key'], 'k-1');
    });

    test('credentials (the browser cookie) are enabled by default', () {
      expect(ApiClient().dio.options.extra['withCredentials'], isTrue);
    });
  });

  group('error mapping', () {
    test('maps the API error structure', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'codigo': 'TEXTO_DEMASIADO_LARGO',
          'mensaje': 'x',
          'detalles': [
            {'campo': 'titulo', 'maximo': 200},
          ],
        }, status: 422),
      );
      final client = ApiClient(dio: Dio()..httpClientAdapter = adapter);
      final error = await client
          .guard(() => client.dio.post<dynamic>('/x'))
          .then<ApiError?>((_) => null, onError: (Object e) => e as ApiError);
      expect(error, isNotNull);
      expect(error!.code, 'TEXTO_DEMASIADO_LARGO');
      expect(error.status, 422);
      expect(error.details.single['maximo'], 200);
      expect(errorMessage(error), contains('200'));
    });

    test('a failed connection becomes a network error', () async {
      final adapter = FakeAdapter(
        (o) => throw DioException(requestOptions: o, type: DioExceptionType.connectionError),
      );
      final client = ApiClient(dio: Dio()..httpClientAdapter = adapter);
      await expectLater(
        client.guard(() => client.dio.get<dynamic>('/x')),
        throwsA(isA<ApiError>().having((f) => f.code, 'code', ApiError.network)),
      );
    });

    test('an unexpected body becomes an unknown error without leaking it', () async {
      final adapter = FakeAdapter((_) => jsonBody({'raro': 'secreto'}, status: 500));
      final client = ApiClient(dio: Dio()..httpClientAdapter = adapter);
      await expectLater(
        client.guard(() => client.dio.get<dynamic>('/x')),
        throwsA(
          isA<ApiError>()
              .having((f) => f.code, 'code', ApiError.unknown)
              .having((f) => errorMessage(f), 'message', isNot(contains('secreto'))),
        ),
      );
    });

    test('every catalog code used by the screens has its own message', () {
      const codes = [
        'CREDENCIALES_INVALIDAS', 'NO_IDENTIFICADA', 'ACCESO_DESACTIVADO',
        'SIN_PERTENENCIA_VIGENTE', 'FECHA_NO_CUBIERTA', 'BITACORA_CERRADA',
        'RECURSO_NO_DISPONIBLE', 'CAMPO_OBLIGATORIO', 'TEXTO_DEMASIADO_LARGO',
        'CLAVE_IDEMPOTENCIA_REUTILIZADA', 'OPERACION_EN_CURSO', 'SOLICITUD_INVALIDA',
        // M2 completo y cierre/reapertura (T1)
        'BITACORA_NO_CERRADA', 'ACTIVIDAD_COMPLETADA', 'ACTIVIDAD_MARCADA_POR_ERROR',
        'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS', 'FECHA_FUTURA_NO_PERMITIDA', 'FECHA_NO_FUTURA',
        'ESTADO_INVALIDO', 'DESCRIPCION_OBLIGATORIA', 'MOTIVO_BLOQUEO_OBLIGATORIO', 'MOTIVO_OBLIGATORIO',
        ApiError.network,
      ];
      final generic = errorMessage(const ApiError(code: 'OTRO', message: ''));
      for (final code in codes) {
        expect(errorMessage(ApiError(code: code, message: '')), isNot(generic), reason: code);
      }
    });
  });
}
