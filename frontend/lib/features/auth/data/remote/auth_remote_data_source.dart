import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../models/session_model.dart';

/// Calls to the session operations of the API.
class AuthRemoteDataSource {
  AuthRemoteDataSource(this._client);

  final ApiClient _client;

  static const _path = '${AppConfig.apiPrefix}/sesion';

  /// M1-01a. The session cookie travels in the response headers; the body has the CSRF token.
  Future<SessionModel> login({required String user, required String password}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        _path,
        data: {'identificador_acceso': user, 'contrasena': password},
      );
      return SessionModel.fromJson(response.data!);
    });
  }

  /// M1-03b. Public; 204 without a body and WITHOUT a session. The code is not retained by this class.
  Future<void> completeFirstAccess({required String identifier, required String code, required String newPassword}) {
    return _redeem('${AppConfig.apiPrefix}/acceso/primer-acceso', identifier, code, newPassword);
  }

  /// M1-09b. Public; 204 without a body, WITHOUT a session. The server revokes every earlier session of the person.
  Future<void> completeRecovery({required String identifier, required String code, required String newPassword}) {
    return _redeem('${AppConfig.apiPrefix}/acceso/recuperacion', identifier, code, newPassword);
  }

  Future<void> _redeem(String path, String identifier, String code, String newPassword) {
    return _client.guard(() async {
      await _client.dio.post<void>(
        path,
        data: {'identificador_acceso': identifier, 'codigo': code, 'contrasena_nueva': newPassword},
      );
    });
  }

  /// M1-01c.
  Future<SessionModel> getSession() {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(_path);
      return SessionModel.fromJson(response.data!);
    });
  }

  /// M1-01b.
  Future<void> logout() {
    return _client.guard(() async {
      await _client.dio.post<void>('$_path/cierre');
    });
  }
}
