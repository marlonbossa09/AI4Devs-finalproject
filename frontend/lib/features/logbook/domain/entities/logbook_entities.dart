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

/// Everything persisted for one date.
class LogbookDay {
  const LogbookDay({required this.logbook, required this.plannings, required this.activities});

  final Logbook logbook;
  final List<Planning> plannings;
  final List<Activity> activities;

  /// The original planning of [activity], if it has one in this day.
  Planning? planningOf(Activity activity) {
    for (final planning in plannings) {
      if (planning.activityId == activity.id) return planning;
    }
    return null;
  }

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
