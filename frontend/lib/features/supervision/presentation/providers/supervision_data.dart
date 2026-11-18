import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/supervision_entities.dart';
import 'supervision_repository.dart';

part 'supervision_data.g.dart';

/// Runs a read; if the server no longer recognizes the session, the app goes back to the login.
Future<T> _guarded<T>(Ref ref, Future<T> Function() call) async {
  try {
    return await call();
  } on ApiError catch (error) {
    if (error.isNotSignedIn) ref.read(authProvider.notifier).expired();
    rethrow;
  }
}

/// What the supervision screen shows: the pages loaded so far (the totals come with every page and count the whole
/// period), the cursor of the next one and the state of a "load more".
class SupervisionFeedState {
  const SupervisionFeedState({required this.first, required this.items, this.next, this.loadingMore = false, this.moreError});

  /// The first page: the period, the cut and the totals.
  final SupervisionPage first;
  final List<SupervisionItem> items;

  /// Opaque cursor for the following page; null when there are no more.
  final String? next;
  final bool loadingMore;

  /// Why the last "load more" failed (the pages already loaded stay on screen).
  final ApiError? moreError;

  bool get hasMore => next != null;
}

/// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
/// never defaulted by the client. It lives only in memory and is dropped with the session.
@riverpod
class SupervisionFeed extends _$SupervisionFeed {
  @override
  Future<SupervisionFeedState> build(DateTime from, DateTime to) async {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    final page = await _guarded(ref, () => ref.read(supervisionRepositoryProvider).getSupervision(from: from, to: to));
    return SupervisionFeedState(first: page, items: page.items, next: page.next);
  }

  /// Loads the next page and appends it. The cursor positions the query, so nothing is repeated or skipped.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.next == null || current.loadingMore) return;
    state = AsyncData(SupervisionFeedState(first: current.first, items: current.items, next: current.next, loadingMore: true));
    try {
      final page = await _guarded(
        ref,
        () => ref.read(supervisionRepositoryProvider).getSupervision(from: from, to: to, cursor: current.next),
      );
      state = AsyncData(SupervisionFeedState(first: current.first, items: [...current.items, ...page.items], next: page.next));
    } on ApiError catch (error) {
      state = AsyncData(SupervisionFeedState(first: current.first, items: current.items, next: current.next, moreError: error));
    }
  }
}

/// The history of one activity (M4-04). `null` = not available (missing, or not readable: the server does not say which).
@riverpod
Future<ActivityHistory?> activityHistory(Ref ref, String activityId) {
  ref.watch(authProvider.select((session) => session.value?.user.id));
  return _guarded(ref, () => ref.read(supervisionRepositoryProvider).getActivityHistory(activityId));
}
