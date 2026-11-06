import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/features/logbook/data/models/logbook_models.dart';
import 'package:smartwork/features/logbook/data/remote/logbook_remote_data_source.dart';
import 'package:smartwork/features/logbook/data/repository/logbook_repository_impl.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/rules/progress_rules.dart';

import '../helpers/fakes.dart';

// Payloads with the shape the M2-06 contract defines (docs/api/m2-bitacoras.md).
const _activityJson = {
  'id': 'a-9',
  'propietaria_id': 'p-1',
  'titulo': 'Atender incidente',
  'origen': 'no_planificada',
  'estado_actual': 'En progreso',
  'marca_error': null,
  'fecha_laboral_origen': '2026-11-06',
  'creada_en': '2026-11-06T16:00:00Z',
};
const _progressJson = {
  'id': 'av-9',
  'actividad_id': 'a-9',
  'fecha_laboral': '2026-11-06',
  'estado': 'En progreso',
  'descripcion': 'Revisé los registros',
  'motivo_bloqueo': null,
  'es_reactivacion': false,
  'registrado_en': '2026-11-06T16:00:00Z',
};

final _today = DateTime.utc(2026, 11, 6);

ApiClient _client(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

Map<String, dynamic> _body({String status = 'En progreso'}) => {
  'actividad': {..._activityJson, 'estado_actual': status},
  'avance': {..._progressJson, 'estado': status},
  'bitacora_creada': true,
};

void main() {
  group('validateUnplanned (CA-54 to CA-58, CA-296)', () {
    ProgressErrors validate({
      String title = 'Atender incidente',
      DateTime? date,
      ActivityStatus? status = ActivityStatus.inProgress,
      String description = 'Revisé los registros',
      String blockReason = '',
    }) => validateUnplanned(
      title: title,
      date: date ?? _today,
      today: _today,
      status: status,
      description: description,
      blockReason: blockReason,
    );

    test('a complete entry has no errors', () {
      expect(validate().isEmpty, isTrue);
    });

    test('the title is required: empty and only spaces are rejected (CA-296, RN-112)', () {
      for (final title in ['', '   ', '\n\t ']) {
        expect(validate(title: title).title, 'El título es obligatorio.', reason: '"$title"');
      }
      expect(validate(title: ' x ').title, isNull);
    });

    test('there is no activity to choose: the activity error never applies', () {
      expect(validate().activity, isNull);
    });

    test('a future date is rejected; today and the past are accepted (CA-43, CA-44, CA-59, CA-60)', () {
      expect(validate(date: DateTime.utc(2026, 11, 7)).date, isNotNull);
      expect(validate(date: _today).date, isNull);
      expect(validate(date: DateTime.utc(2026, 1, 1)).date, isNull);
    });

    test('a status must be chosen, and any of the four is accepted (CA-54)', () {
      expect(validate(status: null).status, 'Elige un estado.');
      for (final status in ActivityStatus.values) {
        final reason = status == ActivityStatus.blocked ? 'Falta acceso' : '';
        expect(validate(status: status, blockReason: reason).isEmpty, isTrue, reason: status.name);
      }
    });

    test('the description is required: empty and only spaces are rejected (CA-58)', () {
      for (final text in ['', '   ']) {
        expect(validate(description: text).description, isNotNull, reason: '"$text"');
      }
    });

    test('blocked requires a reason (CA-55); any other status does not need one', () {
      expect(validate(status: ActivityStatus.blocked).blockReason, 'Indica el motivo del bloqueo.');
      expect(validate(status: ActivityStatus.blocked, blockReason: '  ').blockReason, isNotNull);
      expect(validate(status: ActivityStatus.blocked, blockReason: 'Sin acceso').blockReason, isNull);
      expect(validate(status: ActivityStatus.completed).blockReason, isNull);
    });

    test('every problem is reported at once, each on its own field', () {
      final errors = validate(title: ' ', date: DateTime.utc(2027, 1, 1), status: ActivityStatus.blocked, description: '');
      expect(errors.title, isNotNull);
      expect(errors.date, isNotNull);
      expect(errors.description, isNotNull);
      expect(errors.blockReason, isNotNull);
      expect(errors.isEmpty, isFalse);
    });
  });

  group('M2-06 over the wire', () {
    test('posts to the unplanned-activities resource with the contract fields, the token and the key', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(), status: 201));
      final client = _client(adapter)..csrf = 'csrf-4';
      final result = await LogbookRepositoryImpl(LogbookRemoteDataSource(client)).registerUnplanned(
        date: DateTime.utc(2026, 11, 6),
        title: 'Atender incidente',
        status: ActivityStatus.inProgress,
        description: 'Revisé los registros',
        key: 'key-5',
      );
      final request = adapter.requests.single;
      expect(request.method, 'POST');
      expect(request.path, '/api/v1/mi/actividades-no-planificadas');
      expect(request.headers['Idempotency-Key'], 'key-5');
      expect(request.headers['X-CSRF-Token'], 'csrf-4');
      expect(request.data, {
        'fecha_laboral': '2026-11-06',
        'titulo': 'Atender incidente',
        'estado': 'En progreso',
        'descripcion': 'Revisé los registros',
      });
      expect(result.activity.origin, ActivityOrigin.unplanned);
      expect(result.activity.status, ActivityStatus.inProgress);
      expect(result.progress.description, 'Revisé los registros');
      expect(result.logbookCreated, isTrue);
    });

    test('never sends the origin, the owner, a planning or anything the server decides', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(), status: 201));
      await LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter))).registerUnplanned(
        date: DateTime.utc(2026, 11, 6),
        title: 'T',
        status: ActivityStatus.pending,
        description: 'D',
        key: 'k',
      );
      expect((adapter.requests.single.data as Map).keys.toSet(), {'fecha_laboral', 'titulo', 'estado', 'descripcion'});
    });

    test('the reason travels only with the blocked status', () async {
      final adapter = FakeAdapter((_) => jsonBody(_body(status: 'Bloqueada'), status: 201));
      final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
      await repo.registerUnplanned(
        date: DateTime.utc(2026, 11, 6),
        title: 'T',
        status: ActivityStatus.blocked,
        description: 'D',
        blockReason: 'Falta el acceso',
        key: 'k-1',
      );
      expect(adapter.requests.single.data['motivo_bloqueo'], 'Falta el acceso');
      await repo.registerUnplanned(
        date: DateTime.utc(2026, 11, 6),
        title: 'T',
        status: ActivityStatus.completed,
        description: 'D',
        blockReason: 'sobrante',
        key: 'k-2',
      );
      expect(adapter.requests.last.data.containsKey('motivo_bloqueo'), isFalse);
    });

    test('the response keeps the activity as unplanned and its first entry', () {
      final result = ProgressResultModel.fromJson({
        'actividad': {..._activityJson, 'estado_actual': 'Bloqueada'},
        'avance': {..._progressJson, 'estado': 'Bloqueada', 'motivo_bloqueo': 'Sin acceso'},
        'bitacora_creada': false,
      }).toEntity();
      expect(result.activity.origin, ActivityOrigin.unplanned);
      expect(result.activity.status, ActivityStatus.blocked);
      expect(result.progress.blockReason, 'Sin acceso');
      expect(result.logbookCreated, isFalse);
    });

    test('server rejections reach the caller with their code', () async {
      for (final (code, status) in [
        ('CAMPO_OBLIGATORIO', 422),
        ('FECHA_FUTURA_NO_PERMITIDA', 422),
        ('BITACORA_CERRADA', 409),
        ('MOTIVO_BLOQUEO_OBLIGATORIO', 422),
        ('CLAVE_IDEMPOTENCIA_REUTILIZADA', 422),
      ]) {
        final adapter = FakeAdapter((_) => jsonBody({'codigo': code, 'mensaje': 'x', 'detalles': []}, status: status));
        final repo = LogbookRepositoryImpl(LogbookRemoteDataSource(_client(adapter)));
        await expectLater(
          repo.registerUnplanned(
            date: DateTime.utc(2026, 11, 6),
            title: 'T',
            status: ActivityStatus.inProgress,
            description: 'D',
            key: 'k',
          ),
          throwsA(isA<ApiError>().having((e) => e.code, 'code', code)),
          reason: code,
        );
      }
    });
  });
}
