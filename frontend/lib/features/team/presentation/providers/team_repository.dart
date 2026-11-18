import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/network/api_client_provider.dart';
import '../../data/remote/team_remote_data_source.dart';
import '../../data/repository/team_repository_impl.dart';
import '../../domain/repository/team_repository.dart';

part 'team_repository.g.dart';

@Riverpod(keepAlive: true)
TeamRepository teamRepository(Ref ref) => TeamRepositoryImpl(TeamRemoteDataSource(ref.watch(apiClientProvider)));
