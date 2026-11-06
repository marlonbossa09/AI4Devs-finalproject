import '../../../../core/errors/api_error.dart';
import '../../../../core/network/api_client.dart';
import '../../domain/entities/session.dart';
import '../../domain/repository/auth_repository.dart';
import '../remote/auth_remote_data_source.dart';

class AuthRepositoryImpl implements AuthRepository {
  AuthRepositoryImpl(this._remote, this._client);

  final AuthRemoteDataSource _remote;
  final ApiClient _client;

  @override
  Future<Session> login({required String user, required String password}) async {
    await _remote.login(user: user, password: password);
    // M1-01c supplies what login does not: the server current date.
    return _load();
  }

  @override
  Future<Session?> getSession() async {
    try {
      return await _load();
    } on ApiError catch (error) {
      if (error.isNotSignedIn) {
        _client.csrf = null;
        return null;
      }
      rethrow;
    }
  }

  @override
  Future<void> logout() async {
    try {
      await _remote.logout();
    } finally {
      // Whatever happens, the client forgets the token.
      _client.csrf = null;
    }
  }

  Future<Session> _load() async {
    final model = await _remote.getSession();
    _client.csrf = model.csrf;
    return model.toEntity();
  }
}
