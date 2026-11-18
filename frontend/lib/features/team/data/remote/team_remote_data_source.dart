import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/dates.dart';
import '../models/team_models.dart';

/// Calls to the read-only team operations of the API: M4-05 (members), M4-01 (a colleague's logbook) and M4-02
/// (history). Every one is a GET: the client has no way to write another person's records.
class TeamRemoteDataSource {
  TeamRemoteDataSource(this._client);

  final ApiClient _client;

  static const _teamBase = '${AppConfig.apiPrefix}/equipo';

  /// The server's maximum page size; the member list asks for the largest page to need few requests.
  static const memberPageSize = 100;
  static const historyPageSize = 20;

  /// M4-05.
  Future<TeamMemberPageModel> listMembers({String? cursor}) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '$_teamBase/integrantes',
        queryParameters: {'limite': memberPageSize, if (cursor != null) 'continuar_desde': cursor},
      );
      return TeamMemberPageModel.fromJson(response.data!);
    });
  }

  /// M4-01. Throws `RECURSO_NO_DISPONIBLE` when there is no logbook, or none the user may read.
  Future<PeerLogbookModel> getPeerLogbook({required String personId, required DateTime date}) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/personas/$personId/bitacoras/${formatDate(date)}',
      );
      return PeerLogbookModel.fromJson(response.data!);
    });
  }

  /// M4-02. `desde` and `hasta` are always sent: the server rejects a history without a range.
  Future<HistoryPageModel> getHistory({
    required DateTime from,
    required DateTime to,
    String? personId,
    String? cursor,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/historico',
        queryParameters: {
          'desde': formatDate(from),
          'hasta': formatDate(to),
          if (personId != null) 'persona_id': personId,
          'limite': historyPageSize,
          if (cursor != null) 'continuar_desde': cursor,
        },
      );
      return HistoryPageModel.fromJson(response.data!);
    });
  }
}
