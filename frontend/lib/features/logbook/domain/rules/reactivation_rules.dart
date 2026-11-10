import '../entities/logbook_entities.dart';

/// The states a reactivation can leave the activity in (M3-04). Completada is not one of them: the
/// activity is being taken up again.
const reactivationStatuses = [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked];

/// Whether an activity can be reactivated: it is Completada and is not marked as registered by mistake.
/// The server applies the same rules and has the last word.
bool canReactivate({required ActivityStatus status, required bool marked}) =>
    status == ActivityStatus.completed && !marked;

/// What is wrong with a reactivation form, one message per field (null = fine).
class ReactivationErrors {
  const ReactivationErrors({this.date, this.status, this.description, this.blockReason});

  final String? date;
  final String? status;
  final String? description;
  final String? blockReason;

  bool get isEmpty => date == null && status == null && description == null && blockReason == null;
}

/// Validates a reactivation before sending it (CA-128, CA-129, CA-187 to CA-189, CA-270).
///
/// - the work date cannot be after [today] (a reactivation is execution, RN-27);
/// - it cannot be before the work date of the completion ([completedOn]); the same date is valid;
/// - the status is one of the three allowed;
/// - the description cannot be empty or only spaces;
/// - the reason is required when the status is blocked and is not part of any other status.
ReactivationErrors validateReactivation({
  required DateTime date,
  required DateTime today,
  required DateTime? completedOn,
  required ActivityStatus? status,
  required String description,
  required String blockReason,
}) {
  String? dateError;
  if (date.isAfter(today)) {
    dateError = 'La fecha no puede ser futura: reactivar es registrar trabajo ya realizado.';
  } else if (completedOn != null && date.isBefore(completedOn)) {
    dateError = 'La fecha no puede ser anterior a la de la finalización.';
  }
  return ReactivationErrors(
    date: dateError,
    status: status == null || !reactivationStatuses.contains(status) ? 'Elige uno de los tres estados.' : null,
    description: description.trim().isEmpty ? 'Describe cómo retomas la actividad.' : null,
    blockReason: status == ActivityStatus.blocked && blockReason.trim().isEmpty
        ? 'Indica el motivo del bloqueo.'
        : null,
  );
}
