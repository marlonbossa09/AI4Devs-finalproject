import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
import 'logbook_repository.dart';

part 'activity_list.g.dart';

/// Statuses the activity list is filtered by (empty = all). It filters by CURRENT status (M2-08).
@Riverpod(keepAlive: true)
class ActivityFilter extends _$ActivityFilter {
  @override
  Set<ActivityStatus> build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return {};
  }

  void toggle(ActivityStatus status) {
    final next = {...state};
    if (!next.remove(status)) next.add(status);
    state = next;
  }

  void clear() => state = {};
}

/// What the list shows: the pages loaded so far, the cursor of the next one and the state of a
/// "load more" in progress.
class ActivityListState {
  const ActivityListState({
    required this.items,
    this.next,
    this.loadingMore = false,
    this.moreError,
  });

  final List<ActivitySummary> items;

  /// Opaque cursor for the following page; null when there are no more.
  final String? next;
  final bool loadingMore;

  /// Why the last "load more" failed (the pages already loaded stay on screen).
  final ApiError? moreError;

  bool get hasMore => next != null;
}

/// The user's activities (M2-08), newest first, one page at a time. Changing the filter starts
/// again from the first page.
@riverpod
class ActivityList extends _$ActivityList {
  /// Bumped with every rebuild so a late answer for an old filter cannot overwrite a newer list.
  int _generation = 0;

  List<ActivityStatus> _statuses() => [
    for (final status in ActivityStatus.values)
      if (ref.read(activityFilterProvider).contains(status)) status,
  ];

  @override
  Future<ActivityListState> build() async {
    _generation++;
    ref.watch(activityFilterProvider);
    final page = await _guard(() => ref.read(logbookRepositoryProvider).listActivities(statuses: _statuses()));
    return ActivityListState(items: page.items, next: page.next);
  }

  /// Loads the next page and appends it. A failure keeps the pages already shown and is reported
  /// in [ActivityListState.moreError], so the user can retry.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.next == null || current.loadingMore) return;
    final generation = _generation;
    state = AsyncData(ActivityListState(items: current.items, next: current.next, loadingMore: true));
    try {
      final page = await _guard(
        () => ref.read(logbookRepositoryProvider).listActivities(statuses: _statuses(), cursor: current.next),
      );
      if (generation != _generation) return; // the filter changed meanwhile
      state = AsyncData(ActivityListState(items: [...current.items, ...page.items], next: page.next));
    } on ApiError catch (error) {
      if (generation != _generation) return;
      state = AsyncData(ActivityListState(items: current.items, next: current.next, moreError: error));
    }
  }

  /// If the server no longer recognizes the session, the app goes back to the login.
  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on ApiError catch (error) {
      if (error.isNotSignedIn) ref.read(authProvider.notifier).expired();
      rethrow;
    }
  }
}
