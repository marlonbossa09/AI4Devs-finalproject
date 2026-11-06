import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/network/api_client_provider.dart';
import '../../data/remote/logbook_remote_data_source.dart';
import '../../data/repository/logbook_repository_impl.dart';
import '../../domain/repository/logbook_repository.dart';

part 'logbook_repository.g.dart';

@Riverpod(keepAlive: true)
LogbookRepository logbookRepository(Ref ref) =>
    LogbookRepositoryImpl(LogbookRemoteDataSource(ref.watch(apiClientProvider)));
