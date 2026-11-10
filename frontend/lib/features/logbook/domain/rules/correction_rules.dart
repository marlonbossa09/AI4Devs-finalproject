import '../entities/logbook_entities.dart';
import 'reactivation_rules.dart';

/// Rules of the correction of a progress entry (M3-03). They only mirror what the server decides, to explain a
/// rejection before sending and to offer the right options; the server is the authority.

/// Statuses a correction can leave an entry in. A reactivation is never Completada (IR-11); any other entry can be
/// any of the four.
List<ActivityStatus> correctionStatuses(Progress entry) =>
    entry.isReactivation ? reactivationStatuses : ActivityStatus.values;

/// Whether the entries of an activity can be corrected: not while it is marked as registered by mistake (D-05,
/// CA-297). The mark has to be reverted first.
bool canCorrect(Activity activity) => !activity.marked;

/// Why a sequence of entries breaks IR-11.
enum SequenceProblem {
  /// An ordinary entry right after a Completada, without a reactivation in between.
  progressAfterCompletion,

  /// A reactivation that does not follow a Completada.
  reactivationWithoutCompletion,

  /// A reactivation whose status is Completada.
  reactivationCompleted,
}

/// A breach of IR-11 in the sequence, identified by the entry that suffers it and why.
class SequenceViolation {
  const SequenceViolation(this.progressId, this.problem);

  final String progressId;
  final SequenceProblem problem;

  @override
  bool operator ==(Object other) =>
      other is SequenceViolation && other.progressId == progressId && other.problem == problem;

  @override
  int get hashCode => Object.hash(progressId, problem);
}

/// The breaches of IR-11 in [sequence] (already in work order, as the detail shows it): after a Completada the only
/// valid entry is a reactivation, and a reactivation only follows a Completada and is never Completada itself.
Set<SequenceViolation> sequenceViolations(List<({String id, ActivityStatus status, bool reactivation})> sequence) {
  final result = <SequenceViolation>{};
  ({String id, ActivityStatus status, bool reactivation})? previous;
  for (final entry in sequence) {
    final afterCompletion = previous != null && previous.status == ActivityStatus.completed;
    if (entry.reactivation) {
      if (!afterCompletion) result.add(SequenceViolation(entry.id, SequenceProblem.reactivationWithoutCompletion));
      if (entry.status == ActivityStatus.completed) {
        result.add(SequenceViolation(entry.id, SequenceProblem.reactivationCompleted));
      }
    } else if (afterCompletion) {
      result.add(SequenceViolation(entry.id, SequenceProblem.progressAfterCompletion));
    }
    previous = entry;
  }
  return result;
}

List<({String id, ActivityStatus status, bool reactivation})> _asSequence(
  List<Progress> progress, {
  String? correctedId,
  ActivityStatus? correctedStatus,
}) => [
  for (final entry in progress)
    (
      id: entry.id,
      status: entry.id == correctedId && correctedStatus != null ? correctedStatus : entry.status,
      reactivation: entry.isReactivation,
    ),
];

/// The breaches that correcting [progressId] to [status] would INTRODUCE (PA-29, option A): those the corrected
/// sequence has and the current one does not. A pair that PA-27 admitted and the correction does not touch or worsen
/// is not a reason to reject it. [progress] is the history of the activity in work order.
List<SequenceViolation> newSequenceViolations(List<Progress> progress, String progressId, ActivityStatus status) {
  final before = sequenceViolations(_asSequence(progress));
  final after = sequenceViolations(_asSequence(progress, correctedId: progressId, correctedStatus: status));
  return after.difference(before).toList();
}

/// The current status of the activity after the correction: the status of the last entry of the sequence.
ActivityStatus currentStatusAfter(List<Progress> progress, String progressId, ActivityStatus status) {
  if (progress.isEmpty) return ActivityStatus.pending;
  final last = progress.last;
  return last.id == progressId ? status : last.status;
}

/// What a correction changes: only the fields that differ from [original]. Text is compared and sent without the
/// spaces at its ends. The block reason only counts when the entry ends up blocked; correcting to another status
/// sends no reason (the server clears it, and the audit keeps the previous one).
ProgressCorrection buildCorrection({
  required Progress original,
  required ActivityStatus status,
  required String description,
  required String blockReason,
}) {
  final statusChanged = status != original.status;
  final text = description.trim();
  final reason = blockReason.trim();
  final reasonChanged = status == ActivityStatus.blocked && (statusChanged || reason != (original.blockReason ?? '').trim());
  return ProgressCorrection(
    status: statusChanged ? status : null,
    description: text != original.description.trim() ? text : null,
    blockReason: reasonChanged ? reason : null,
  );
}

/// What is wrong with a correction (all null / false = fine).
class CorrectionErrors {
  const CorrectionErrors({this.description, this.blockReason, this.nothingChanged = false, this.sequence});

  final String? description;
  final String? blockReason;

  /// The form equals the entry as it is: there is nothing to correct.
  final bool nothingChanged;

  /// The correction would break the sequence of the activity.
  final String? sequence;

  bool get isEmpty => description == null && blockReason == null && !nothingChanged && sequence == null;
}

/// The sentence that explains a breach of the sequence.
String sequenceProblemMessage(SequenceProblem problem) => switch (problem) {
  SequenceProblem.progressAfterCompletion =>
    'Esta corrección dejaría un avance posterior a una finalización sin reactivación.',
  SequenceProblem.reactivationWithoutCompletion =>
    'Esta corrección dejaría una reactivación que ya no sigue a una finalización.',
  SequenceProblem.reactivationCompleted => 'Una reactivación no puede quedar Completada.',
};

/// Validates a correction of [original] as the form holds it. [progress] is the history of the activity in work
/// order, including [original].
CorrectionErrors validateCorrection({
  required Progress original,
  required List<Progress> progress,
  required ActivityStatus status,
  required String description,
  required String blockReason,
}) {
  final descriptionError = description.trim().isEmpty ? 'La descripción no puede quedar vacía.' : null;
  final reasonError = status == ActivityStatus.blocked && blockReason.trim().isEmpty ? 'Indica el motivo del bloqueo.' : null;
  if (descriptionError != null || reasonError != null) {
    return CorrectionErrors(description: descriptionError, blockReason: reasonError);
  }
  final correction = buildCorrection(original: original, status: status, description: description, blockReason: blockReason);
  if (correction.isEmpty) return const CorrectionErrors(nothingChanged: true);
  final violations = newSequenceViolations(progress, original.id, status);
  if (violations.isNotEmpty) return CorrectionErrors(sequence: sequenceProblemMessage(violations.first.problem));
  return const CorrectionErrors();
}
