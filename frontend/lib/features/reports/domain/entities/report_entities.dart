import '../../../logbook/domain/entities/logbook_entities.dart' show ActivityOrigin, ActivityStatus;

/// The public answer of M5-01 and M5-02 (contracts, version 0.2), as the app keeps it: a CLOSED projection. The app never
/// computes a figure, never infers a status or a title the server left out and never keeps a report anywhere but in memory
/// (a report is read on screen and is not edited nor stored: RN-56).

/// The period a report covers: the work dates asked for, both ends included.
class ReportPeriod {
  const ReportPeriod({required this.from, required this.to});

  final DateTime from;
  final DateTime to;
}

/// The person a report is about. Only the identifier and the name: nothing else about a person reaches the app.
class ReportPerson {
  const ReportPerson({required this.id, required this.name});

  final String id;
  final String name;
}

/// The counts of activities by their status AT THE CUT (the last day of the period). [unavailable] groups the activities
/// whose status at the cut the server may not tell (it was set by another team's record): it is a COUNT, never a status.
class StatusAtCutCounts {
  const StatusAtCutCounts({
    required this.pending,
    required this.inProgress,
    required this.blocked,
    required this.completed,
    required this.unavailable,
  });

  final int pending;
  final int inProgress;
  final int blocked;
  final int completed;
  final int unavailable;
}

/// The six deterministic metrics (D-M5-04), exactly as the server calculated them. The app only shows them.
class ReportMetrics {
  const ReportMetrics({
    required this.progressEntries,
    required this.workdays,
    required this.activities,
    required this.planned,
    required this.unplanned,
    required this.originUnavailable,
    required this.withBlock,
    required this.statusAtCut,
  });

  /// `avances`: progress entries authorized in the period.
  final int progressEntries;

  /// `jornadas_con_registros`: distinct work dates with authorized entries.
  final int workdays;

  /// `actividades_con_registros`: distinct activities with authorized entries.
  final int activities;

  /// `actividades_por_origen`.
  final int planned;
  final int unplanned;

  /// Activities of another team: their origin is protected and is not inferred.
  final int originUnavailable;

  /// `actividades_con_bloqueo`: activities with some authorized Bloqueada entry in the period (NOT "blocked now").
  final int withBlock;

  /// `actividades_por_estado_al_corte`.
  final StatusAtCutCounts statusAtCut;
}

/// An activity of the report. [ref] is opaque and LOCAL to the report (`a1`, `a2`…): never a database identifier. A neutral
/// activity (started in another team) carries NO title and NO origin: the server sends none and the app never asks.
class ReportActivity {
  const ReportActivity({required this.ref, required this.isNeutral, this.title, this.origin});

  final String ref;
  final bool isNeutral;

  /// Only in the full form.
  final String? title;
  final ActivityOrigin? origin;
}

/// One authorized progress entry. [status] is the HISTORICAL status of that entry, not the current one of the activity.
class ReportFact {
  const ReportFact({
    required this.date,
    required this.activityRef,
    required this.status,
    required this.description,
    this.blockReason,
  });

  final DateTime date;
  final String activityRef;
  final ActivityStatus status;

  /// Free text written by a person: it is shown as plain text, never interpreted.
  final String description;

  /// Only when [status] is Bloqueada.
  final String? blockReason;
}

/// One time an activity was blocked (an authorized Bloqueada entry): a HISTORICAL record, not the current state.
class BlockageOccurrence {
  const BlockageOccurrence({required this.date, required this.reason});

  final DateTime date;
  final String reason;
}

/// The blockages of one activity, grouped (P-3).
class ReportBlockage {
  const ReportBlockage({required this.activityRef, required this.occurrences});

  final String activityRef;
  final List<BlockageOccurrence> occurrences;
}

/// What a report says about ONE person: the verifiable part (metrics, activities, entries, blockages) and, apart, the
/// narrative the AI wrote from it (a list of plain-text sections, or null when there is none).
class ReportBody {
  const ReportBody({
    required this.metrics,
    required this.activities,
    required this.facts,
    required this.blockages,
    required this.narrative,
  });

  /// Null when the report has no data.
  final ReportMetrics? metrics;
  final List<ReportActivity> activities;
  final List<ReportFact> facts;
  final List<ReportBlockage> blockages;

  /// Sections of generated text; null when there is no narrative (no data).
  final List<String>? narrative;

  ReportActivity? activityOf(String ref) {
    for (final activity in activities) {
      if (activity.ref == ref) return activity;
    }
    return null;
  }
}

/// M5-01: the report of one person.
class IndividualReport {
  const IndividualReport({
    required this.period,
    required this.generatedAt,
    required this.baseStatement,
    required this.noData,
    required this.person,
    required this.body,
  });

  final ReportPeriod period;
  final DateTime generatedAt;

  /// The fixed product statement of what the report is based on (P-6). It comes with every report, also without data.
  final String baseStatement;
  final bool noData;
  final ReportPerson person;
  final ReportBody body;
}

/// One person of the team report with their own body.
class TeamReportPerson {
  const TeamReportPerson({required this.person, required this.body});

  final ReportPerson person;
  final ReportBody body;
}

/// M5-02: the report of the team. Only people with at least one authorized entry appear. The team section is DETERMINISTIC
/// (no narrative).
class TeamReport {
  const TeamReport({
    required this.period,
    required this.generatedAt,
    required this.baseStatement,
    required this.noData,
    required this.people,
    required this.teamMetrics,
  });

  final ReportPeriod period;
  final DateTime generatedAt;
  final String baseStatement;
  final bool noData;
  final List<TeamReportPerson> people;

  /// Null when the report has no data.
  final ReportMetrics? teamMetrics;
}
