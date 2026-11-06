import '../entities/logbook_entities.dart';

/// Contract of the logbook operations (M2-01a, M2-01b, M2-03). Errors are thrown as `ApiError`.
abstract class LogbookRepository {
  /// Returns what is persisted for [date], or `null` when there is no logbook for it.
  /// Consulting never creates anything (D-01).
  Future<LogbookDay?> getLogbook(DateTime date);

  /// Opens the logbook of [date]. Idempotent: if it already exists it is returned unchanged.
  Future<OpenResult> openLogbook(DateTime date);

  /// Creates a planned activity (status pending) with its original planning. [key] identifies
  /// ONE intention and is reused when retrying it.
  Future<PlanResult> createActivity({
    required DateTime date,
    required String title,
    String? description,
    required String key,
  });
}
