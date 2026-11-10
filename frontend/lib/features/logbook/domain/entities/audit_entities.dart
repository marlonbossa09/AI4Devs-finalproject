/// The kinds of record whose audit can be consulted from the app (M3-07). A planning has an audit too, but no
/// operation audits it today (plannings are not edited), so the app offers no way to open it.
enum AuditObjectType { logbook, activity, progress }

/// The operations an audit entry can record (RN-49): what was done to the record.
enum AuditOperation {
  closing,
  reopening,
  correction,
  pastDayChange,
  reactivation,
  errorMark,
  markReversal,

  /// An operation this version of the app does not know: it is still shown, with its raw name.
  other,
}

/// One entry of the audit (M3-07): who did what to a record, when, and which values changed. It is NOT a progress
/// entry of the work: the audit records changes to the records, the work history records the work itself.
class AuditEntry {
  const AuditEntry({
    required this.id,
    required this.moment,
    required this.operationName,
    required this.operation,
    required this.objectType,
    required this.objectId,
    this.authorId,
    this.workDate,
    this.reason,
    this.previous,
    this.next,
  });

  final String id;

  /// Real moment of the operation.
  final DateTime moment;

  /// The operation as the server names it (`cierre`, `correccion`...).
  final String operationName;
  final AuditOperation operation;
  final String objectType;
  final String objectId;

  /// Who did it. Never shown as a name: the app says "Tú" for the signed-in user and nothing about anyone else.
  final String? authorId;

  /// Work date of the audited record (for an activity, the day it was created).
  final DateTime? workDate;

  /// Why it was done; mandatory for a reopening and a mark.
  final String? reason;

  /// The values before and after, only the fields the operation affected.
  final Map<String, dynamic>? previous;
  final Map<String, dynamic>? next;
}

/// A page of the audit of ONE record, in chronological order. [next] is the opaque cursor of the following page,
/// or null when there are no more.
class AuditPage {
  const AuditPage({required this.items, this.next});

  final List<AuditEntry> items;
  final String? next;
}
