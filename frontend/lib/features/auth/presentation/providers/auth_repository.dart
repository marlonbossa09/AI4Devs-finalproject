import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/network/api_client_provider.dart';
import '../../data/remote/auth_remote_data_source.dart';
import '../../data/repository/auth_repository_impl.dart';
import '../../domain/repository/auth_repository.dart';

part 'auth_repository.g.dart';

@Riverpod(keepAlive: true)
AuthRepository authRepository(Ref ref) {
  final client = ref.watch(apiClientProvider);
  return AuthRepositoryImpl(AuthRemoteDataSource(client), client);
}
