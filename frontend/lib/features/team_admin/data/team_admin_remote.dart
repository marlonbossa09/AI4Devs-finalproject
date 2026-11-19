import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../config/app_config.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_client_provider.dart';
import '../../../core/utils/dates.dart';

/// A code of first access, shown ONCE: the server returns it in this single answer and keeps only its HMAC.
class FirstAccessCode {
  const FirstAccessCode({required this.code, required this.expiresAt});

  final String code;
  final DateTime expiresAt;
}

/// Calls of the supervisor's team management (M1-11 to M1-13). The server decides everything (who may, which team, which
/// role): the client sends only a name and an access identifier, and never a role or a team.
class TeamAdminRemote {
  TeamAdminRemote(this._client);

  final ApiClient _client;

  static const _base = '${AppConfig.apiPrefix}/equipo/integrantes';

  /// M1-11. Returns the id of the new collaborator.
  Future<String> createCollaborator({required String name, required String accessId}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        _base,
        data: {'nombre': name, 'identificador_acceso': accessId},
      );
      return response.data!['persona_id'] as String;
    });
  }

  /// M1-12. A new code replaces the previous one that was still pending.
  Future<FirstAccessCode> issueFirstAccessCode(String personId) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>('$_base/$personId/codigo-primer-acceso');
      final data = response.data!;
      return FirstAccessCode(code: data['codigo'] as String, expiresAt: DateTime.parse(data['caduca_en'] as String));
    });
  }

  /// M1-13. Returns the date the membership ends (it is always a future date: until then the person is still a member).
  Future<DateTime> endMembership(String personId) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>('$_base/$personId/finalizacion');
      return parseDate(response.data!['fecha_efectiva'] as String);
    });
  }
}

final teamAdminRemoteProvider = Provider<TeamAdminRemote>((ref) => TeamAdminRemote(ref.watch(apiClientProvider)));
