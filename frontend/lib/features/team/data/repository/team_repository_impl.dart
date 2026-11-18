import '../../../../core/errors/api_error.dart';
import '../../domain/entities/team_entities.dart';
import '../../domain/repository/team_repository.dart';
import '../remote/team_remote_data_source.dart';

class TeamRepositoryImpl implements TeamRepository {
  TeamRepositoryImpl(this._remote);

  final TeamRemoteDataSource _remote;

  @override
  Future<TeamMemberPage> listMembers({String? cursor}) async => (await _remote.listMembers(cursor: cursor)).toEntity();

  @override
  Future<PeerLogbook?> getPeerLogbook({required String personId, required DateTime date}) async {
    try {
      return (await _remote.getPeerLogbook(personId: personId, date: date)).toEntity();
    } on ApiError catch (error) {
      // "Not available" is a normal answer: the server says the same for no logbook and for one the user may not read.
      if (error.code == 'RECURSO_NO_DISPONIBLE') return null;
      rethrow;
    }
  }

  @override
  Future<HistoryPage> getHistory({
    required DateTime from,
    required DateTime to,
    String? personId,
    String? cursor,
  }) async => (await _remote.getHistory(from: from, to: to, personId: personId, cursor: cursor)).toEntity();
}
