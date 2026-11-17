import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client_provider.dart';
import '../../data/remote/auth_remote_data_source.dart';
import '../../data/repository/access_code_repository_impl.dart';
import '../../domain/repository/access_code_repository.dart';

/// Repository of the redemption of one-time codes. It keeps no state: the screens read it only when the person submits.
final accessCodeRepositoryProvider = Provider<AccessCodeRepository>(
  (ref) => AccessCodeRepositoryImpl(AuthRemoteDataSource(ref.watch(apiClientProvider))),
);
