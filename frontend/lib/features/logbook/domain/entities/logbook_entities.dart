/// Position of a date relative to today (RN-72).
enum DateType { past, today, future }

/// The four activity states (RN-08).
enum ActivityStatus { pending, inProgress, blocked, completed }

/// Whether the activity was planned or not. It is an identification, not a state (RN-20).
enum ActivityOrigin { planned, unplanned }

/// Original planning or planned continuation (RN-76).
enum PlanningType { original, continuation }

/// The work log of one user for one date. Three dates are kept apart (RN-18): the work date,
/// the real creation moment and the real modification moment.
class Logbook {
  const Logbook({
    required this.id,
    required this.userId,
    required this.date,
    required this.dateType,
    required this.closed,
    required this.summary,
    required this.createdAt,
    required this.updatedAt,
    this.closedAt,
  });

  final String id;
  final String userId;
  final DateTime date;
  final DateType dateType;
  final bool closed;
  final String summary;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? closedAt;
}

class Activity {
  const Activity({
    required this.id,
    required this.userId,
    required this.title,
    required this.origin,
    required this.status,
    required this.date,
    required this.createdAt,
    this.marked = false,
    this.markReason,
  });

  final String id;
  final String userId;
  final String title;
  final ActivityOrigin origin;

  /// Current status: derived from the last progress entry; pending if there is none.
  final ActivityStatus status;

  /// Work date of the logbook where the activity was created.
  final DateTime date;
  final DateTime createdAt;

  /// Whether it carries an error mark (registered by mistake).
  final bool marked;

  /// Why it was marked, when it was.
  final String? markReason;

  ActivitySummary get summary => ActivitySummary(id: id, title: title, origin: origin, status: status);
}

/// The minimum of an activity needed to choose it or list it (M2-08): who it is, what it is called,
/// how it started and its current status.
class ActivitySummary {
  const ActivitySummary({
    required this.id,
    required this.title,
    required this.origin,
    required this.status,
  });

  final String id;
  final String title;
  final ActivityOrigin origin;
  final ActivityStatus status;
}

/// A page of the activity list (M2-08). [next] is the opaque cursor of the following page, or null
/// when there are no more.
class ActivityListPage {
  const ActivityListPage({required this.items, this.next});

  final List<ActivitySummary> items;
  final String? next;
}

/// One activity with everything recorded about it (M2-07): what was planned, apart from what was
/// done, and its current status.
class ActivityDetail {
  const ActivityDetail({
    required this.activity,
    required this.progress,
    required this.plannedContinuations,
    required this.status,
    this.originalPlanning,
  });

  final Activity activity;

  /// What was foreseen when the activity was planned. Null for an unplanned activity (IR-16).
  final Planning? originalPlanning;

  /// Continuations foreseen for later days. They are NOT progress entries (IR-14).
  final List<Planning> plannedContinuations;

  /// Execution entries in sequence order: work date, registration moment, stable id (IR-09).
  final List<Progress> progress;
  final ActivityStatus status;
}

/// What was foreseen for a date. It is NOT a progress entry: it does not change the status.
class Planning {
  const Planning({
    required this.id,
    required this.activityId,
    required this.date,
    required this.type,
    required this.description,
    required this.createdAt,
  });

  final String id;
  final String activityId;
  final DateTime date;
  final PlanningType type;
  final String description;
  final DateTime createdAt;
}

/// One execution progress entry (RN-17, RN-65). It keeps the status the activity had when it was
/// recorded, so later changes never rewrite it.
class Progress {
  const Progress({
    required this.id,
    required this.activityId,
    required this.date,
    required this.status,
    required this.description,
    required this.createdAt,
    this.blockReason,
    this.isReactivation = false,
  });

  final String id;
  final String activityId;

  /// Work date of the logbook it belongs to.
  final DateTime date;
  final ActivityStatus status;
  final String description;
  final DateTime createdAt;

  /// Only present when [status] is blocked (RN-24).
  final String? blockReason;
  final bool isReactivation;
}

/// Everything persisted for one date.
class LogbookDay {
  const LogbookDay({
    required this.logbook,
    required this.plannings,
    required this.activities,
    this.progress = const [],
  });

  final Logbook logbook;
  final List<Planning> plannings;
  final List<Activity> activities;

  /// Progress entries recorded in this logbook, in the order the server sends them.
  final List<Progress> progress;

  /// The original planning of [activity], if it has one in this day.
  Planning? planningOf(Activity activity) {
    for (final planning in plannings) {
      if (planning.activityId == activity.id) return planning;
    }
    return null;
  }

  /// The progress entries of [activity] recorded in this day.
  List<Progress> progressOf(Activity activity) =>
      progress.where((p) => p.activityId == activity.id).toList();

  int count(ActivityStatus status) => activities.where((a) => a.status == status).length;
}

class OpenResult {
  const OpenResult({required this.created, required this.logbook});

  final bool created;
  final Logbook logbook;
}

class PlanResult {
  const PlanResult({required this.activity, required this.planning, required this.logbookCreated});

  final Activity activity;
  final Planning planning;
  final bool logbookCreated;
}

/// Result of recording a progress entry: the entry and the activity with its recalculated status.
class ProgressResult {
  const ProgressResult({required this.progress, required this.activity, required this.logbookCreated});

  final Progress progress;
  final Activity activity;
  final bool logbookCreated;
}
