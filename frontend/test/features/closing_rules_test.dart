import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/models/logbook_models.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/closing_rules.dart';

import '../helpers/fakes.dart';

final _day = DateTime.utc(2026, 11, 6);

Logbook _logbook({String summary = 'Resumen', bool closed = false, DateType type = DateType.today}) => Logbook(
  id: 'b1',
  userId: 'p1',
  date: _day,
  dateType: type,
  closed: closed,
  summary: summary,
  createdAt: DateTime.utc(2026, 11, 6, 8),
  updatedAt: DateTime.utc(2026, 11, 6, 9),
  closedAt: closed ? DateTime.utc(2026, 11, 6, 18) : null,
);

Activity _activity(String id, {DateTime? date, bool marked = false}) => Activity(
  id: id,
  userId: 'p1',
  title: 'Actividad $id',
  origin: ActivityOrigin.planned,
  status: ActivityStatus.pending,
  date: date ?? _day,
  createdAt: DateTime.utc(2026, 11, 6, 8),
  marked: marked,
);

Progress _progress(String activityId) => Progress(
  id: 'pr-$activityId',
  activityId: activityId,
  date: _day,
  status: ActivityStatus.inProgress,
  description: 'Avancé',
  createdAt: DateTime.utc(2026, 11, 6, 10),
);

Planning _continuation(String activityId) => Planning(
  id: 'pc-$activityId',
  activityId: activityId,
  date: _day,
  type: PlanningType.continuation,
  description: 'Seguir',
  createdAt: DateTime.utc(2026, 11, 5, 10),
);

LogbookDay _dayWith({
  String summary = 'Resumen',
  List<Activity> activities = const [],
  List<Progress> progress = const [],
  List<Planning> plannings = const [],
}) => LogbookDay(
  logbook: _logbook(summary: summary),
  plannings: plannings,
  activities: activities,
  progress: progress,
);

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

Map<String, dynamic> _body({bool closed = true}) => {
  'bitacora': {
    'id': 'b1',
    'persona_id': 'p1',
    'fecha_laboral': '2026-11-06',
    'clase_jornada': 'actual',
    'estado': closed ? 'cerrada' : 'abierta',
    'resumen': 'Resumen',
    'cerrada_en': closed ? '2026-11-06T18:00:00Z' : null,
    'creada_en': '2026-11-06T08:00:00Z',
    'modificada_en': '2026-11-06T09:00:00Z',
  },
};

LogbookRepositoryImpl _repo(FakeAdapter adapter, {String csrf = 'csrf-4'}) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)..csrf = csrf));

void main() {
  group('closingConditions (RN-21, RN-109)', () {
    test('a summary with text and an activity created in the day meets them (CA-90)', () {
      final c = closingConditions(_dayWith(activities: [_activity('a1')]));
      expect(c.hasSummary, isTrue);
      expect(c.hasActivity, isTrue);
      expect(c.met, isTrue);
      expect(c.missing, isEmpty);
    });

    test('an empty summary or one of only spaces does not (CA-93, CA-94)', () {
      for (final summary in ['', '   ', '\n\t  ']) {
        final c = closingConditions(_dayWith(summary: summary, activities: [_activity('a1')]));
        expect(c.hasSummary, isFalse, reason: '"$summary"');
        expect(c.met, isFalse);
        expect(c.missing, hasLength(1));
      }
    });

    test('a day without any activity does not (CA-92)', () {
      final c = closingConditions(_dayWith());
      expect(c.hasActivity, isFalse);
      expect(c.missing.single, contains('actividad'));
    });

    test('an activity created on another day counts only with a progress entry of this day (CA-91)', () {
      final other = _activity('a2', date: DateTime.utc(2026, 11, 3));
      expect(closingConditions(_dayWith(activities: [other])).hasActivity, isFalse);
      expect(closingConditions(_dayWith(activities: [other], progress: [_progress('a2')])).hasActivity, isTrue);
    });

    test('a planned continuation does not count as a continued activity (CA-184)', () {
      final other = _activity('a2', date: DateTime.utc(2026, 11, 3));
      final c = closingConditions(_dayWith(activities: [other], plannings: [_continuation('a2')]));
      expect(c.hasActivity, isFalse);
    });

    test('an activity marked as registered by mistake does not count (CA-283)', () {
      final marked = _activity('a1', marked: true);
      expect(closingConditions(_dayWith(activities: [marked])).hasActivity, isFalse);
      expect(closingConditions(_dayWith(activities: [marked, _activity('a3')])).hasActivity, isTrue);
    });

    test('a progress entry on a marked activity does not count either', () {
      final marked = _activity('a2', date: DateTime.utc(2026, 11, 3), marked: true);
      expect(closingConditions(_dayWith(activities: [marked], progress: [_progress('a2')])).hasActivity, isFalse);
    });

    test('everything missing is reported at once, one sentence each', () {
      expect(closingConditions(_dayWith(summary: ' ')).missing, hasLength(2));
    });
  });

  group('canOfferClosing (CA-97)', () {
    test('an open past or current day can be closed', () {
      expect(canOfferClosing(_logbook(type: DateType.today)), isTrue);
      expect(canOfferClosing(_logbook(type: DateType.past)), isTrue);
    });

    test('a future day cannot', () {
      expect(canOfferClosing(_logbook(type: DateType.future)), isFalse);
    });

    test('a day that is already closed is not offered for closing', () {
      expect(canOfferClosing(_logbook(closed: true)), isFalse);
    });
  });

  group('the reopening reason (RN-50, CA-100)', () {
    test('is mandatory: empty and only spaces are rejected', () {
      for (final reason in ['', '   ', '\n\t ']) {
        expect(validateReopenReason(reason), 'Indica el motivo de la reapertura.', reason: '"$reason"');
      }
    });

    test('any text is accepted', () {
      expect(validateReopenReason('Olvidé una cifra'), isNull);
    });
  });

  group('missingFromDetails', () {
    test('turns what the server said into sentences, and ignores what it does not know', () {
      expect(missingFromDetails([{'campo': 'resumen', 'motivo': 'vacio'}]), hasLength(1));
      expect(
        missingFromDetails([
          {'campo': 'resumen', 'motivo': 'vacio'},
          {'campo': 'actividades', 'motivo': 'x'},
          {'campo': 'otra_cosa', 'motivo': 'x'},
        ]),
        hasLength(2),
      );
      expect(missingFromDetails(const []), isEmpty);
    });
  });

  group('M3-01 and M3-02 over the wire', () {
    test('closing posts to the closing resource of that date, with the token and the key, and no body', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body()));
      final logbook = await _repo(adapter).closeLogbook(date: _day, key: 'key-1');
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/bitacoras/2026-11-06/cierre');
      expect(request.headers['Idempotency-Key'], 'key-1');
      expect(request.headers['X-CSRF-Token'], 'csrf-4');
      expect(request.data, isNull);
      expect(logbook.closed, isTrue);
      expect(logbook.closedAt, DateTime.utc(2026, 11, 6, 18));
    });

    test('reopening posts to the reopening resource with only the reason, the token and the key', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(closed: false)));
      final logbook = await _repo(adapter).reopenLogbook(date: _day, reason: 'Corregir una cifra', key: 'key-2');
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/bitacoras/2026-11-06/reapertura');
      expect(request.headers['Idempotency-Key'], 'key-2');
      expect(request.headers['X-CSRF-Token'], 'csrf-4');
      expect(request.data, {'motivo': 'Corregir una cifra'});
      expect(logbook.closed, isFalse);
      expect(logbook.closedAt, isNull);
    });

    test('the response is the logbook as the server holds it: its three dates and its summary', () {
      final logbook = LogbookResultModel.fromJson(_body()).toEntity();
      expect(logbook.date, _day);
      expect(logbook.summary, 'Resumen');
      expect(logbook.createdAt, DateTime.utc(2026, 11, 6, 8));
      expect(logbook.updatedAt, DateTime.utc(2026, 11, 6, 9));
    });

    test('server rejections reach the caller with their code', () async {
      for (final (code, status) in [
        ('CONDICIONES_DE_CIERRE_NO_CUMPLIDAS', 409),
        ('BITACORA_CERRADA', 409),
        ('BITACORA_NO_CERRADA', 409),
        ('FECHA_FUTURA_NO_PERMITIDA', 422),
        ('MOTIVO_OBLIGATORIO', 422),
        ('TEXTO_DEMASIADO_LARGO', 422),
        ('RECURSO_NO_DISPONIBLE', 404),
        ('CLAVE_IDEMPOTENCIA_REUTILIZADA', 422),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        await expectLater(
          _repo(adapter).closeLogbook(date: _day, key: 'k'),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: 'close $code',
        );
        await expectLater(
          _repo(adapter).reopenLogbook(date: _day, reason: 'x', key: 'k'),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: 'reopen $code',
        );
      }
    });

    test('the details of a rejected closing reach the caller', () async {
      final adapter = FakeAdapter(
        (_) => jsonBody({
          'codigo': 'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS',
          'mensaje': 'x',
          'detalles': [
            {'campo': 'resumen', 'motivo': 'vacio'},
          ],
        }, status: 409),
      );
      try {
        await _repo(adapter).closeLogbook(date: _day, key: 'k');
        fail('should have thrown');
      } on ApiError catch (error) {
        expect(error.details.single['campo'], 'resumen');
      }
    });

    test('every rejection has its own clear message in Spanish', () {
      for (final code in [
        'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS',
        'BITACORA_CERRADA',
        'BITACORA_NO_CERRADA',
        'FECHA_FUTURA_NO_PERMITIDA',
        'MOTIVO_OBLIGATORIO',
        'RECURSO_NO_DISPONIBLE',
      ]) {
        final message = errorMessage(ApiError(code: code, message: 'texto del servidor', status: 409));
        expect(message, isNot(contains('texto del servidor')), reason: code);
        expect(message, isNot('Se produjo un error inesperado. Inténtalo de nuevo.'), reason: code);
      }
    });
  });
}
