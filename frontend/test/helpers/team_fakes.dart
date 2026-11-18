import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/team/domain/entities/team_entities.dart';
import 'package:smartwork/features/team/domain/repository/team_repository.dart';

import 'fakes.dart';

/// In-memory "server" of the team reads. It records what the screen asked for.
class FakeTeamRepository implements TeamRepository {
  FakeTeamRepository({List<TeamMember>? members}) : members = members ?? defaultMembers;

  /// Current members. `p1` is the signed-in user (see [sampleSession]).
  List<TeamMember> members;

  /// Logbooks by `personId|yyyy-mm-dd`.
  final Map<String, PeerLogbook> logbooks = {};

  /// Every history entry the user may read, in server order; the fake pages them by [pageSize].
  List<HistoryEntry> history = [];
  int pageSize = 2;

  ApiError? membersError;
  ApiError? logbookError;
  ApiError? historyError;

  /// Errors for the next "load more" calls (null = succeed), in order.
  final List<ApiError?> moreErrors = [];

  final List<Map<String, Object?>> historyRequests = [];
  final List<Map<String, Object?>> logbookRequests = [];
  int memberRequests = 0;

  static const defaultMembers = [
    TeamMember(id: 'p1', name: 'Carlos Colaborador', role: TeamRole.collaborator),
    TeamMember(id: 'p2', name: 'Ana Compañera', role: TeamRole.collaborator),
    TeamMember(id: 'p3', name: 'Sara Supervisora', role: TeamRole.supervisor),
  ];

  @override
  Future<TeamMemberPage> listMembers({String? cursor}) async {
    memberRequests++;
    final error = membersError;
    if (error != null) throw error;
    return TeamMemberPage(items: members);
  }

  @override
  Future<PeerLogbook?> getPeerLogbook({required String personId, required DateTime date}) async {
    logbookRequests.add({'personId': personId, 'date': date});
    final error = logbookError;
    if (error != null) throw error;
    return logbooks['$personId|${date.toIso8601String().substring(0, 10)}'];
  }

  @override
  Future<HistoryPage> getHistory({
    required DateTime from,
    required DateTime to,
    String? personId,
    String? cursor,
  }) async {
    historyRequests.add({'from': from, 'to': to, 'personId': personId, 'cursor': cursor});
    if (cursor != null && moreErrors.isNotEmpty) {
      final error = moreErrors.removeAt(0);
      if (error != null) throw error;
    }
    final error = historyError;
    if (error != null) throw error;
    final all = [for (final e in history) if (personId == null || e.ownerId == personId) e];
    final start = cursor == null ? 0 : int.parse(cursor);
    final end = (start + pageSize).clamp(0, all.length);
    return HistoryPage(items: all.sublist(start, end), next: end < all.length ? '$end' : null);
  }
}

/// A full activity as a colleague sees it.
SharedActivity fullActivity(String id, String title, {ActivityStatus? status, String? markReason, String owner = 'p2'}) =>
    SharedActivity(id: id, ownerId: owner, form: ActivityForm.full, title: title, origin: ActivityOrigin.planned, status: status, markReason: markReason);

/// A neutral activity: it carries nothing but its id and owner.
SharedActivity neutralActivity(String id, {String owner = 'p2'}) =>
    SharedActivity(id: id, ownerId: owner, form: ActivityForm.neutral);

PeerLogbook peerLogbook({
  String owner = 'p2',
  String summary = 'Resumen de Ana',
  bool closed = false,
  List<SharedActivity> activities = const [],
  List<PeerProgress> progress = const [],
  List<PeerPlanning> plannings = const [],
}) => PeerLogbook(
  ownerId: owner,
  date: today,
  closed: closed,
  summary: summary,
  plannings: plannings,
  progress: progress,
  activities: activities,
);

HistoryEntry historyEntry(String owner, DateTime date, {String summary = 'Resumen', List<SharedActivity> activities = const []}) =>
    HistoryEntry(ownerId: owner, date: date, closed: false, summary: summary, activities: activities);
