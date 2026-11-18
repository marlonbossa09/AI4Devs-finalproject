import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/network/api_client_provider.dart';
import '../../data/remote/supervision_remote_data_source.dart';
import '../../data/repository/supervision_repository_impl.dart';
import '../../domain/repository/supervision_repository.dart';

part 'supervision_repository.g.dart';

@Riverpod(keepAlive: true)
SupervisionRepository supervisionRepository(Ref ref) =>
    SupervisionRepositoryImpl(SupervisionRemoteDataSource(ref.watch(apiClientProvider)));
