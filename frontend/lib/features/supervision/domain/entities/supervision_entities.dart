import '../../../logbook/domain/entities/logbook_entities.dart';
import '../../../team/domain/entities/team_entities.dart';

/// Why an activity is in the supervision view (M4-03, RN-47). An activity can have several.
enum InclusionReason { plannedInPeriod, withProgressInPeriod, pendingAtCut }

/// One element of the supervision view. It is either an activity ([SupervisedActivity], in its `full` or `neutral`
/// form) or a minimal reference ([MinimalReference]): the contract tells them apart by `tipo`.
sealed class SupervisionItem {
  const SupervisionItem({required this.ownerId, required this.activity});

  final String ownerId;

  /// `full` or `neutral`. A minimal reference always carries a neutral one.
  final SharedActivity activity;
}

/// An activity of the team in the period. [statusAtCut] is what the server decided can be shown: when it is null the
/// status at the cut is NOT available (it would come from another team's records) and the client does not guess it.
/// [currentStatusIfDiffers] is present only when the server reports it (the status at the cut is shown, it differs from
/// the current one and the owner is in the team today).
class SupervisedActivity extends SupervisionItem {
  const SupervisedActivity({
    required super.ownerId,
    required super.activity,
    required this.reasons,
    this.statusAtCut,
    this.currentStatusIfDiffers,
  });

  final List<InclusionReason> reasons;
  final ActivityStatus? statusAtCut;
  final ActivityStatus? currentStatusIfDiffers;
}

/// A minimal reference (D-09, RN-84, RN-89): an activity started in another team with no records of this one. Only the
/// owner, that it started elsewhere, the current status and, if the server allows it, the date of the last progress.
/// It is NOT access to the activity history: no title, no descriptions, no status at the cut.
class MinimalReference extends SupervisionItem {
  const MinimalReference({
    required super.ownerId,
    required super.activity,
    required this.currentStatus,
    this.lastProgressDate,
  });

  final ActivityStatus currentStatus;
  final DateTime? lastProgressDate;
}

/// How many elements are shown without a status at the cut (they are NOT in the totals by status).
class WithoutStatusCount {
  const WithoutStatusCount({required this.minimalReferences, required this.activities});

  final int minimalReferences;
  final int activities;
}

/// A page of the supervision view (M4-03). The totals count the whole period, not just this page.
class SupervisionPage {
  const SupervisionPage({
    required this.from,
    required this.to,
    required this.cut,
    required this.totals,
    required this.withoutStatus,
    required this.items,
    this.next,
  });

  final DateTime from;
  final DateTime to;

  /// The cut of the status at the cut: the last day of the period.
  final DateTime cut;
  final Map<ActivityStatus, int> totals;
  final WithoutStatusCount withoutStatus;
  final List<SupervisionItem> items;
  final String? next;
}

/// The history of one activity as the supervisor may read it (M4-04): the activity with only the authorized progress and
/// plannings, or a minimal reference.
sealed class ActivityHistory {
  const ActivityHistory();
}

/// `tipo: actividad`. [activity] is `full` (the title is authorized) or `neutral` ("Actividad en continuidad"). The
/// progress is in historical order as the server sends it; nothing here is derived or completed by the client.
class ActivityHistoryDetail extends ActivityHistory {
  const ActivityHistoryDetail({
    required this.activity,
    required this.progress,
    required this.plannings,
    this.currentStatus,
  });

  final SharedActivity activity;
  final List<PeerProgress> progress;
  final List<PeerPlanning> plannings;

  /// Only when the owner is in the team today.
  final ActivityStatus? currentStatus;
}

/// `tipo: referencia_minima`: the whole answer is the reference, nothing more.
class ActivityHistoryReference extends ActivityHistory {
  const ActivityHistoryReference(this.reference);

  final MinimalReference reference;
}
