import '../entities/supervision_entities.dart';

/// Reads of the supervision: the consolidated view of the team (M4-03) and the history of one activity (M4-04). The
/// audit (M3-07) is read through the existing logbook repository. Everything is read-only and the server decides
/// what each element is: the client never infers a status, a title or a date that the server left out.
abstract interface class SupervisionRepository {
  /// One page of the supervision view for the period [from]-[to], both included (M4-03).
  Future<SupervisionPage> getSupervision({required DateTime from, required DateTime to, String? cursor});

  /// The history of [activityId] (M4-04), or `null` when the server says it is not available (it answers the same for
  /// a missing activity and for one the supervisor may not read).
  Future<ActivityHistory?> getActivityHistory(String activityId);
}
