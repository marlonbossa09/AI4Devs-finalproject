import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/dates.dart';
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
}
