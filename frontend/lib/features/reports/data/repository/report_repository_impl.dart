import '../../domain/entities/report_entities.dart';
import '../../domain/repository/report_repository.dart';
import '../remote/report_remote_data_source.dart';

class ReportRepositoryImpl implements ReportRepository {
  ReportRepositoryImpl(this._remote);

  final ReportRemoteDataSource _remote;

  @override
  Future<IndividualReport> generateIndividual({required DateTime from, required DateTime to, String? personId}) =>
      _remote.generateIndividual(from: from, to: to, personId: personId);

  @override
  Future<TeamReport> generateTeam({required DateTime from, required DateTime to}) => _remote.generateTeam(from: from, to: to);
}
