import '../../../../core/errors/api_error.dart';
import '../../domain/entities/supervision_entities.dart';
import '../../domain/repository/supervision_repository.dart';
import '../remote/supervision_remote_data_source.dart';

class SupervisionRepositoryImpl implements SupervisionRepository {
  SupervisionRepositoryImpl(this._remote);

  final SupervisionRemoteDataSource _remote;

  @override
  Future<SupervisionPage> getSupervision({required DateTime from, required DateTime to, String? cursor}) =>
      _remote.getSupervision(from: from, to: to, cursor: cursor);

  @override
  Future<ActivityHistory?> getActivityHistory(String activityId) async {
    try {
      return await _remote.getActivityHistory(activityId);
    } on ApiError catch (error) {
      // "Not available" is a normal answer: the server says the same for a missing activity and for one that is not readable.
      if (error.code == 'RECURSO_NO_DISPONIBLE') return null;
      rethrow;
    }
  }
}
