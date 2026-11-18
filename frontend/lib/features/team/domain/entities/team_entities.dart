import '../../../logbook/domain/entities/logbook_entities.dart';

/// Role a team member holds today (M4-05). Only these two exist.
enum TeamRole { collaborator, supervisor }

/// One current member of the user's team (M4-05). It is the MINIMUM needed to choose a colleague: who they
/// are, what they are called and their role. Nothing else about a person is kept by the client.
class TeamMember {
  const TeamMember({required this.id, required this.name, required this.role});

  final String id;
  final String name;
  final TeamRole role;
}

/// A page of the team member list. [next] is the opaque cursor of the following page, or null.
class TeamMemberPage {
  const TeamMemberPage({required this.items, this.next});

  final List<TeamMember> items;
  final String? next;
}

/// How an activity reaches the reader (RA-04): `full` for whoever is authorized on the day it started, `neutral`
/// for everyone else. A neutral activity carries NO title, origin, mark or date: the server sends none and the
/// client never asks for them.
enum ActivityForm { full, neutral }

/// The label every neutral activity shows (RN-101). Fixed text: it never comes from the payload.
const neutralActivityLabel = 'Actividad en continuidad';

/// An activity as another person sees it (`ActividadVisible`, convenciones 7).
class SharedActivity {
  const SharedActivity({
    required this.id,
    required this.ownerId,
    required this.form,
    this.title,
    this.origin,
    this.status,
    this.markReason,
  });

  final String id;
  final String ownerId;
  final ActivityForm form;

  /// Only in the `full` form.
  final String? title;
  final ActivityOrigin? origin;

  /// Current status, only when the server reports it (the owner still belongs to the team).
  final ActivityStatus? status;

  /// Why it was marked as registered by mistake, only in the `full` form and only when it was.
  final String? markReason;

  bool get isNeutral => form == ActivityForm.neutral;
  bool get isMarked => markReason != null;
}

/// A progress entry of another person (own detail only, RA-05): what was done and, if blocked, why.
class PeerProgress {
  const PeerProgress({
    required this.activityId,
    required this.date,
    required this.status,
    required this.description,
    this.blockReason,
  });

  final String activityId;
  final DateTime date;
  final ActivityStatus status;
  final String description;
  final String? blockReason;
}

/// What another person foresaw for a date.
class PeerPlanning {
  const PeerPlanning({required this.activityId, required this.date, required this.type, required this.description});

  final String activityId;
  final DateTime date;
  final PlanningType type;
  final String description;
}

/// The logbook of a colleague for one date, read-only (M4-01).
class PeerLogbook {
  const PeerLogbook({
    required this.ownerId,
    required this.date,
    required this.closed,
    required this.summary,
    required this.plannings,
    required this.progress,
    required this.activities,
  });

  final String ownerId;
  final DateTime date;
  final bool closed;
  final String summary;
  final List<PeerPlanning> plannings;
  final List<PeerProgress> progress;
  final List<SharedActivity> activities;
}

/// One logbook of the history (M4-02).
class HistoryEntry {
  const HistoryEntry({
    required this.ownerId,
    required this.date,
    required this.closed,
    required this.summary,
    required this.activities,
  });

  final String ownerId;
  final DateTime date;
  final bool closed;
  final String summary;
  final List<SharedActivity> activities;
}

/// A page of the history. [next] is the opaque cursor of the following page, or null.
class HistoryPage {
  const HistoryPage({required this.items, this.next});

  final List<HistoryEntry> items;
  final String? next;
}
