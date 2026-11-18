import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/network/api_client_provider.dart';
import '../../data/remote/report_remote_data_source.dart';
import '../../data/repository/report_repository_impl.dart';
import '../../domain/repository/report_repository.dart';

part 'report_repository.g.dart';

@Riverpod(keepAlive: true)
ReportRepository reportRepository(Ref ref) => ReportRepositoryImpl(ReportRemoteDataSource(ref.watch(apiClientProvider)));
