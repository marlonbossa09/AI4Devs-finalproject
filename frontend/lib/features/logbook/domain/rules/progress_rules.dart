import '../entities/logbook_entities.dart';

/// What is wrong with a progress form, one message per field (null = fine).
///
/// These checks only avoid a useless round trip: the server validates the same rules and has the
/// last word (CA-48, CA-49, CA-68, CA-69, CA-182).
class ProgressErrors {
  const ProgressErrors({this.activity, this.title, this.date, this.status, this.description, this.blockReason});

  final String? activity;

  /// Only used when the entry creates an unplanned activity (M2-06).
  final String? title;
  final String? date;
  final String? status;
  final String? description;
  final String? blockReason;

  bool get isEmpty =>
      activity == null &&
      title == null &&
      date == null &&
      status == null &&
      description == null &&
      blockReason == null;
}

/// Validates a progress entry before sending it.
///
/// - an activity must be chosen;
/// - the work date cannot be after [today] (no future execution, RN-27);
/// - a status must be chosen;
/// - the description cannot be empty or only spaces (RN-70);
/// - the reason is required when the status is blocked (RN-24) and is not part of any other status.
ProgressErrors validateProgress({
  required String? activityId,
  required DateTime date,
  required DateTime today,
  required ActivityStatus? status,
  required String description,
  required String blockReason,
}) {
  return ProgressErrors(
    activity: activityId == null ? 'Elige la actividad.' : null,
    date: date.isAfter(today) ? 'La fecha no puede ser futura: solo se registra lo ya realizado.' : null,
    status: status == null ? 'Elige un estado.' : null,
    description: description.trim().isEmpty ? 'Describe el trabajo realizado.' : null,
    blockReason: status == ActivityStatus.blocked && blockReason.trim().isEmpty
        ? 'Indica el motivo del bloqueo.'
        : null,
  );
}

/// Validates an UNPLANNED activity before sending it (M2-06): the title is required (RN-112, CA-296)
/// and its first progress entry follows the same rules as any progress entry (CA-54 to CA-58). The
/// server validates the same and has the last word.
ProgressErrors validateUnplanned({
  required String title,
  required DateTime date,
  required DateTime today,
  required ActivityStatus? status,
  required String description,
  required String blockReason,
}) {
  final progress = validateProgress(
    activityId: 'new', // there is no activity yet: it is created by this operation
    date: date,
    today: today,
    status: status,
    description: description,
    blockReason: blockReason,
  );
  return ProgressErrors(
    title: title.trim().isEmpty ? 'El título es obligatorio.' : null,
    date: progress.date,
    status: progress.status,
    description: progress.description,
    blockReason: progress.blockReason,
  );
}
