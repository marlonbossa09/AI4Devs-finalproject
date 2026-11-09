import '../entities/logbook_entities.dart';

/// Contract of the logbook operations (M2-01a, M2-01b, M2-02, M2-03, M2-04, M2-05, M2-06, M2-07, M2-08, M3-01, M3-02). Errors are thrown as `ApiError`.
abstract class LogbookRepository {
  /// Returns what is persisted for [date], or `null` when there is no logbook for it.
  /// Consulting never creates anything (D-01).
  Future<LogbookDay?> getLogbook(DateTime date);

  /// Opens the logbook of [date]. Idempotent: if it already exists it is returned unchanged.
  Future<OpenResult> openLogbook(DateTime date);

  /// Saves (replaces) the free summary of the logbook of [date] (M2-02). An empty text is valid: it
  /// only prevents closing the day. It is a replacement, so it needs no idempotency key.
  Future<SummaryResult> saveSummary({required DateTime date, required String summary});

  /// Creates a planned activity (status pending) with its original planning. [key] identifies
  /// ONE intention and is reused when retrying it.
  Future<PlanResult> createActivity({
    required DateTime date,
    required String title,
    String? description,
    required String key,
  });

  /// One of the user's activities with its plannings and progress history (M2-07). Throws
  /// `RECURSO_NO_DISPONIBLE` when it does not exist or is not the user's.
  Future<ActivityDetail> getActivity(String id);

  /// The user's activities, newest first (M2-08). [statuses] filters by CURRENT status (empty =
  /// all). Pass the [cursor] of the previous page to get the next one.
  Future<ActivityListPage> listActivities({
    List<ActivityStatus> statuses = const [],
    int? limit,
    String? cursor,
  });

  /// Records work that was not planned (M2-06): creates the activity, flagged as unplanned, and its
  /// first progress entry in ONE operation. The activity starts with that entry's status. [key]
  /// identifies ONE intention and is reused when retrying it.
  Future<ProgressResult> registerUnplanned({
    required DateTime date,
    required String title,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  });

  /// Closes the logbook of [date] (M3-01). Only the owner, manually, with a summary with text and at
  /// least one activity created or continued in it. Returns the logbook as the server holds it now.
  /// [key] identifies ONE intention and is reused when retrying it.
  Future<Logbook> closeLogbook({required DateTime date, required String key});

  /// Reopens the closed logbook of [date] (M3-02). The [reason] is mandatory and is kept in the audit.
  /// Returns the logbook as the server holds it now. [key] identifies ONE intention.
  Future<Logbook> reopenLogbook({required DateTime date, required String reason, required String key});

  /// Plans the continuation of an activity of the signed-in user for a later day (M2-04). It is a
  /// planning: it creates no progress entry and does not change the status. [description] is
  /// optional. [key] identifies ONE intention and is reused when retrying it.
  Future<ContinuationResult> planContinuation({
    required String activityId,
    required DateTime date,
    String? description,
    required String key,
  });

  /// Records a progress entry on an activity of the signed-in user (M2-05). [blockReason] is only
  /// sent for the blocked status. [key] identifies ONE intention and is reused when retrying it.
  Future<ProgressResult> registerProgress({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  });
}
