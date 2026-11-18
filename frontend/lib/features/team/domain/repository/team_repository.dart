import '../entities/team_entities.dart';

/// Reads of the team: who the colleagues are (M4-05), a colleague's logbook (M4-01) and the history (M4-02).
/// Everything is read-only and everything is decided by the server: the client never filters by permission.
abstract interface class TeamRepository {
  /// One page of the current members of the user's team (M4-05).
  Future<TeamMemberPage> listMembers({String? cursor});

  /// The logbook of [personId] for [date] (M4-01). `null` when the server says it is not available: no logbook, or
  /// not one the user may read (the server answers the same, so the client cannot tell which).
  Future<PeerLogbook?> getPeerLogbook({required String personId, required DateTime date});

  /// One page of the logbooks the user may read between [from] and [to], both included (M4-02), optionally only
  /// those of [personId].
  Future<HistoryPage> getHistory({required DateTime from, required DateTime to, String? personId, String? cursor});
}
