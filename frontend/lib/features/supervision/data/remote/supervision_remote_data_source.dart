import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/dates.dart';
import '../../domain/entities/supervision_entities.dart';
import '../models/supervision_models.dart';

/// Calls to the read-only supervision operations: M4-03 (the consolidated view) and M4-04 (the history of an activity).
/// Every one is a GET. The server decides who may call them: a collaborator gets a 403 `OPERACION_NO_PERMITIDA`.
class SupervisionRemoteDataSource {
  SupervisionRemoteDataSource(this._client);

  final ApiClient _client;

  static const _base = '${AppConfig.apiPrefix}/equipo';
  static const pageSize = 20;

  /// M4-03. `desde` and `hasta` are always sent (there is no `corte` parameter: the cut is the last day).
  Future<SupervisionPage> getSupervision({required DateTime from, required DateTime to, String? cursor}) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '$_base/supervision',
        queryParameters: {
          'desde': formatDate(from),
          'hasta': formatDate(to),
          'limite': pageSize,
          if (cursor != null) 'continuar_desde': cursor,
        },
      );
      return SupervisionPageModel.fromJson(response.data!).page;
    });
  }

  /// M4-04. Throws `RECURSO_NO_DISPONIBLE` when the activity is missing or the supervisor may not read it.
  Future<ActivityHistory> getActivityHistory(String activityId) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>('$_base/actividades/$activityId');
      return activityHistoryFromJson(response.data!);
    });
  }
}
