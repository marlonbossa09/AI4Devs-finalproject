import '../../domain/repository/access_code_repository.dart';
import '../remote/auth_remote_data_source.dart';

class AccessCodeRepositoryImpl implements AccessCodeRepository {
  AccessCodeRepositoryImpl(this._remote);

  final AuthRemoteDataSource _remote;

  @override
  Future<void> redeem(
    AccessCodePurpose purpose, {
    required String identifier,
    required String code,
    required String newPassword,
  }) {
    return switch (purpose) {
      AccessCodePurpose.firstAccess => _remote.completeFirstAccess(identifier: identifier, code: code, newPassword: newPassword),
      AccessCodePurpose.recovery => _remote.completeRecovery(identifier: identifier, code: code, newPassword: newPassword),
    };
  }
}
