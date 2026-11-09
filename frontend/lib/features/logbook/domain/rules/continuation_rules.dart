import '../entities/logbook_entities.dart';

/// Whether a continuation can be planned for an activity (M2-04): a Completada activity is not
/// continued until it is reactivated (RN-78) and one marked as registered by mistake never is.
/// The server applies the same rules and has the last word.
bool canPlanContinuation({required ActivityStatus status, required bool marked}) =>
    !marked && status != ActivityStatus.completed;

/// What is wrong with a continuation form, one message per field (null = fine).
class ContinuationErrors {
  const ContinuationErrors({this.date});

  final String? date;

  bool get isEmpty => date == null;
}

/// Validates a planned continuation before sending it.
///
/// The work date must be AFTER [today] (RN-76): today and the past are for progress, not planning.
/// The description is optional (D-03). The check only avoids a useless round trip: the server
/// validates the same rule and has the last word (`FECHA_NO_FUTURA`).
ContinuationErrors validateContinuation({required DateTime date, required DateTime today}) {
  return ContinuationErrors(
    date: date.isAfter(today) ? null : 'Elige una fecha posterior a hoy.',
  );
}
