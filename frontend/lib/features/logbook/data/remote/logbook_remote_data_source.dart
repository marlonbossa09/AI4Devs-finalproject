import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/dates.dart';
import '../../domain/entities/logbook_entities.dart';
import '../models/logbook_models.dart';

/// Calls to the logbook operations of the API (`/mi/...`: always the caller own records).
class LogbookRemoteDataSource {
  LogbookRemoteDataSource(this._client);

  final ApiClient _client;

  static const _base = '${AppConfig.apiPrefix}/mi/bitacoras';

  /// M2-01a. Throws `RECURSO_NO_DISPONIBLE` when there is no logbook for the date.
  Future<LogbookDayModel> getLogbook(DateTime date) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>('$_base/${formatDate(date)}');
      return LogbookDayModel.fromJson(response.data!);
    });
  }

  /// M2-01b.
  Future<OpenResultModel> openLogbook(DateTime date) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        _base,
        data: {'fecha_laboral': formatDate(date)},
      );
      return OpenResultModel.fromJson(response.data!);
    });
  }

  /// M2-03. `Idempotency-Key` is mandatory.
  Future<PlanResultModel> createActivity({
    required DateTime date,
    required String title,
    String? description,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '$_base/${formatDate(date)}/planificaciones',
        data: {'titulo': title, if (description != null) 'descripcion': description},
        options: _client.withKey(key),
      );
      return PlanResultModel.fromJson(response.data!);
    });
  }

  /// M2-07. Throws `RECURSO_NO_DISPONIBLE` when it does not exist or is not the user's.
  Future<ActivityDetailModel> getActivity(String id) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>('${AppConfig.apiPrefix}/mi/actividades/$id');
      return ActivityDetailModel.fromJson(response.data!);
    });
  }

  /// M2-08. Only the parameters of the contract: `estado` (repeated, one per status), `limite` and
  /// `continuar_desde`. There is no text search.
  Future<ActivityListModel> listActivities({
    List<ActivityStatus> statuses = const [],
    int? limit,
    String? cursor,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades',
        queryParameters: {
          if (statuses.isNotEmpty) 'estado': [for (final s in statuses) statusToWire(s)],
          'limite': ?limit,
          'continuar_desde': ?cursor,
        },
      );
      return ActivityListModel.fromJson(response.data!);
    });
  }

  /// M2-06. `Idempotency-Key` is mandatory. The body has no origin, no owner and no planning: the
  /// server decides the origin. The block reason only travels with the blocked status.
  Future<ProgressResultModel> registerUnplanned({
    required DateTime date,
    required String title,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades-no-planificadas',
        data: {
          'fecha_laboral': formatDate(date),
          'titulo': title,
          'estado': statusToWire(status),
          'descripcion': description,
          if (status == ActivityStatus.blocked && blockReason != null) 'motivo_bloqueo': blockReason,
        },
        options: _client.withKey(key),
      );
      return ProgressResultModel.fromJson(response.data!);
    });
  }

  /// M2-05. `Idempotency-Key` is mandatory. The block reason only travels with the blocked status.
  Future<ProgressResultModel> registerProgress({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades/$activityId/avances',
        data: {
          'fecha_laboral': formatDate(date),
          'estado': statusToWire(status),
          'descripcion': description,
          if (status == ActivityStatus.blocked && blockReason != null) 'motivo_bloqueo': blockReason,
        },
        options: _client.withKey(key),
      );
      return ProgressResultModel.fromJson(response.data!);
    });
  }
}
