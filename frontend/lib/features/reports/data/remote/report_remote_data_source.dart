import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/dates.dart';
import '../../domain/entities/report_entities.dart';
import '../models/report_models.dart';

/// Calls to M5-01 and M5-02. Both are POST (the CSRF token is added by the client) and neither changes nor stores anything.
/// They carry no idempotency key and the client never repeats them by itself. No timeout is set here: a generation can
/// legitimately take minutes, and the global timeouts are not changed to accommodate it.
class ReportRemoteDataSource {
  ReportRemoteDataSource(this._client);

  final ApiClient _client;

  static const _base = '${AppConfig.apiPrefix}/informes';

  Future<IndividualReport> generateIndividual({required DateTime from, required DateTime to, String? personId}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '$_base/individuales',
        data: {'desde': formatDate(from), 'hasta': formatDate(to), if (personId != null) 'persona_id': personId},
      );
      return individualReportFromJson(response.data!);
    });
  }

  Future<TeamReport> generateTeam({required DateTime from, required DateTime to}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '$_base/consolidados',
        data: {'desde': formatDate(from), 'hasta': formatDate(to)},
      );
      return teamReportFromJson(response.data!);
    });
  }
}
