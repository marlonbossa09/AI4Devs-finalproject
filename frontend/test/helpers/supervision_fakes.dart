import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/supervision/domain/entities/supervision_entities.dart';
import 'package:smartwork/features/supervision/domain/repository/supervision_repository.dart';

import 'team_fakes.dart';

/// In-memory "server" of the supervision reads. It records what the screen asked for.
class FakeSupervisionRepository implements SupervisionRepository {
  /// Every element the supervisor may read, in server order; the fake pages them by [pageSize].
  List<SupervisionItem> items = [];
  int pageSize = 2;
  Map<ActivityStatus, int> totals = {
    ActivityStatus.pending: 1,
    ActivityStatus.inProgress: 2,
    ActivityStatus.blocked: 0,
    ActivityStatus.completed: 1,
  };
  WithoutStatusCount withoutStatus = const WithoutStatusCount(minimalReferences: 1, activities: 1);

  /// Histories by activity id (a missing id is "not available").
  final Map<String, ActivityHistory> histories = {};

  ApiError? supervisionError;
  ApiError? historyError;
  final List<ApiError?> moreErrors = [];
  final List<Map<String, Object?>> supervisionRequests = [];
  final List<String> historyRequests = [];

  @override
  Future<SupervisionPage> getSupervision({required DateTime from, required DateTime to, String? cursor}) async {
    supervisionRequests.add({'from': from, 'to': to, 'cursor': cursor});
    if (cursor != null && moreErrors.isNotEmpty) {
      final error = moreErrors.removeAt(0);
      if (error != null) throw error;
    }
    final error = supervisionError;
    if (error != null) throw error;
    final start = cursor == null ? 0 : int.parse(cursor);
    final end = (start + pageSize).clamp(0, items.length);
    return SupervisionPage(
      from: from,
      to: to,
      cut: to,
      totals: totals,
      withoutStatus: withoutStatus,
      items: items.sublist(start, end),
      next: end < items.length ? '$end' : null,
    );
  }

  @override
  Future<ActivityHistory?> getActivityHistory(String activityId) async {
    historyRequests.add(activityId);
    final error = historyError;
    if (error != null) throw error;
    return histories[activityId];
  }
}

SupervisedActivity supervised(
  String id,
  String title, {
  String owner = 'p2',
  List<InclusionReason> reasons = const [InclusionReason.pendingAtCut],
  ActivityStatus? atCut = ActivityStatus.inProgress,
  ActivityStatus? currentIfDiffers,
}) => SupervisedActivity(
  ownerId: owner,
  activity: fullActivity(id, title, owner: owner),
  reasons: reasons,
  statusAtCut: atCut,
  currentStatusIfDiffers: currentIfDiffers,
);

SupervisedActivity supervisedNeutral(String id, {String owner = 'p2', ActivityStatus? atCut}) => SupervisedActivity(
  ownerId: owner,
  activity: neutralActivity(id, owner: owner),
  reasons: const [InclusionReason.withProgressInPeriod],
  statusAtCut: atCut,
);

MinimalReference minimalReference(String id, {String owner = 'p2', ActivityStatus status = ActivityStatus.inProgress, DateTime? last}) =>
    MinimalReference(ownerId: owner, activity: neutralActivity(id, owner: owner), currentStatus: status, lastProgressDate: last);
