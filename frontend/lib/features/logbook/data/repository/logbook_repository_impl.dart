import '../../../../core/errors/api_error.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/repository/logbook_repository.dart';
import '../remote/logbook_remote_data_source.dart';

class LogbookRepositoryImpl implements LogbookRepository {
  LogbookRepositoryImpl(this._remote);

  final LogbookRemoteDataSource _remote;

  @override
  Future<LogbookDay?> getLogbook(DateTime date) async {
    try {
      return (await _remote.getLogbook(date)).toEntity();
    } on ApiError catch (error) {
      // No logbook for that date is a normal situation, not an error.
      if (error.code == 'RECURSO_NO_DISPONIBLE') return null;
      rethrow;
    }
  }

  @override
  Future<OpenResult> openLogbook(DateTime date) async => (await _remote.openLogbook(date)).toEntity();

  @override
  Future<PlanResult> createActivity({
    required DateTime date,
    required String title,
    String? description,
    required String key,
  }) async {
    final model = await _remote.createActivity(
      date: date,
      title: title,
      description: description,
      key: key,
    );
    return model.toEntity();
  }

  @override
  Future<ActivityDetail> getActivity(String id) async => (await _remote.getActivity(id)).toEntity();

  @override
  Future<ActivityListPage> listActivities({
    List<ActivityStatus> statuses = const [],
    int? limit,
    String? cursor,
  }) async => (await _remote.listActivities(statuses: statuses, limit: limit, cursor: cursor)).toEntity();

  @override
  Future<ProgressResult> registerUnplanned({
    required DateTime date,
    required String title,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final model = await _remote.registerUnplanned(
      date: date,
      title: title,
      status: status,
      description: description,
      blockReason: blockReason,
      key: key,
    );
    return model.toEntity();
  }

  @override
  Future<ProgressResult> registerProgress({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final model = await _remote.registerProgress(
      activityId: activityId,
      date: date,
      status: status,
      description: description,
      blockReason: blockReason,
      key: key,
    );
    return model.toEntity();
  }
}
