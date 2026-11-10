import '../../../../core/errors/api_error.dart';
import '../../domain/entities/audit_entities.dart';
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
  Future<SummaryResult> saveSummary({required DateTime date, required String summary}) async =>
      (await _remote.saveSummary(date: date, summary: summary)).toEntity();

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
  Future<Logbook> closeLogbook({required DateTime date, required String key}) async =>
      (await _remote.closeLogbook(date: date, key: key)).toEntity();

  @override
  Future<Logbook> reopenLogbook({required DateTime date, required String reason, required String key}) async =>
      (await _remote.reopenLogbook(date: date, reason: reason, key: key)).toEntity();

  @override
  Future<ContinuationResult> planContinuation({
    required String activityId,
    required DateTime date,
    String? description,
    required String key,
  }) async {
    final model = await _remote.planContinuation(
      activityId: activityId,
      date: date,
      description: description,
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

  @override
  Future<ProgressResult> reactivateActivity({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final model = await _remote.reactivateActivity(
      activityId: activityId,
      date: date,
      status: status,
      description: description,
      blockReason: blockReason,
      key: key,
    );
    return model.toEntity();
  }

  @override
  Future<MarkResult> markActivityAsError({
    required String activityId,
    required String reason,
    required String key,
  }) async {
    final model = await _remote.markActivityAsError(activityId: activityId, reason: reason, key: key);
    return model.toEntity();
  }

  @override
  Future<MarkResult> revertActivityMark({required String activityId, required String key}) async {
    final model = await _remote.revertActivityMark(activityId: activityId, key: key);
    return model.toEntity();
  }

  @override
  Future<CorrectionResult> correctProgress({
    required String progressId,
    required ProgressCorrection correction,
    required String key,
  }) async {
    final model = await _remote.correctProgress(progressId: progressId, correction: correction, key: key);
    return model.toEntity();
  }

  @override
  Future<AuditPage> listAudit({
    required AuditObjectType type,
    required String objectId,
    int? limit,
    String? cursor,
  }) async => (await _remote.listAudit(type: type, objectId: objectId, limit: limit, cursor: cursor)).toEntity();
}
