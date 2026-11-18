import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/team_entities.dart';
import 'team_repository.dart';

part 'team_data.g.dart';

/// Runs a read; if the server no longer recognizes the session, the app goes back to the login.
Future<T> _guarded<T>(Ref ref, Future<T> Function() call) async {
  try {
    return await call();
  } on ApiError catch (error) {
    if (error.isNotSignedIn) ref.read(authProvider.notifier).expired();
    rethrow;
  }
}

/// A safety bound on the member list: a team is small; this only stops a misbehaving server from looping the client.
const _maxMemberPages = 20;

/// The current members of the user's team (M4-05), every page, as the server orders them (name, id). It lives only
/// in memory and is dropped with the session; it is never written to any storage.
@riverpod
Future<List<TeamMember>> teamMembers(Ref ref) async {
  ref.watch(authProvider.select((session) => session.value?.user.id));
  final members = <TeamMember>[];
  String? cursor;
  for (var page = 0; page < _maxMemberPages; page++) {
    final result = await _guarded(ref, () => ref.read(teamRepositoryProvider).listMembers(cursor: cursor));
    members.addAll(result.items);
    cursor = result.next;
    if (cursor == null) break;
  }
  return members;
}

/// The logbook of a colleague for one date (M4-01), read-only. `null` = not available (no logbook, or none the user may
/// read: the server does not say which).
@riverpod
Future<PeerLogbook?> peerLogbook(Ref ref, String personId, DateTime date) {
  ref.watch(authProvider.select((session) => session.value?.user.id));
  return _guarded(ref, () => ref.read(teamRepositoryProvider).getPeerLogbook(personId: personId, date: date));
}

/// What the history screen shows: the pages loaded so far, the cursor of the next one and the state of a "load more".
class HistoryViewState {
  const HistoryViewState({required this.items, this.next, this.loadingMore = false, this.moreError});

  final List<HistoryEntry> items;

  /// Opaque cursor for the following page; null when there are no more.
  final String? next;
  final bool loadingMore;

  /// Why the last "load more" failed (the pages already loaded stay on screen).
  final ApiError? moreError;

  bool get hasMore => next != null;
}

/// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
/// always sent, never defaulted by the client.
@riverpod
class HistoryView extends _$HistoryView {
  @override
  Future<HistoryViewState> build(DateTime from, DateTime to, String? personId) async {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    final page = await _guarded(
      ref,
      () => ref.read(teamRepositoryProvider).getHistory(from: from, to: to, personId: personId),
    );
    return HistoryViewState(items: page.items, next: page.next);
  }

  /// Loads the next page and appends it. The cursor positions the query, so nothing is repeated or skipped.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.next == null || current.loadingMore) return;
    state = AsyncData(HistoryViewState(items: current.items, next: current.next, loadingMore: true));
    try {
      final page = await _guarded(
        ref,
        () => ref.read(teamRepositoryProvider).getHistory(from: from, to: to, personId: personId, cursor: current.next),
      );
      state = AsyncData(HistoryViewState(items: [...current.items, ...page.items], next: page.next));
    } on ApiError catch (error) {
      state = AsyncData(HistoryViewState(items: current.items, next: current.next, moreError: error));
    }
  }
}
