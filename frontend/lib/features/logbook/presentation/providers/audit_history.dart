import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/audit_entities.dart';
import 'logbook_repository.dart';

part 'audit_history.g.dart';

/// What the audit screen shows: the pages loaded so far, the cursor of the next one and the state of a "load more"
/// in progress.
class AuditHistoryState {
  const AuditHistoryState({
    required this.items,
    this.next,
    this.loadingMore = false,
    this.moreError,
  });

  /// The entries loaded so far, in chronological order (oldest first), as the server sends them.
  final List<AuditEntry> items;

  /// Opaque cursor for the following page; null when there are no more.
  final String? next;
  final bool loadingMore;

  /// Why the last "load more" failed (the pages already loaded stay on screen).
  final ApiError? moreError;

  bool get hasMore => next != null;
}

/// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
/// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.
@riverpod
class AuditHistory extends _$AuditHistory {
  @override
  Future<AuditHistoryState> build(AuditObjectType type, String objectId) async {
    final page = await _guard(() => ref.read(logbookRepositoryProvider).listAudit(type: type, objectId: objectId));
    return AuditHistoryState(items: page.items, next: page.next);
  }

  /// Loads the next page and appends it, without repeating or skipping entries (the cursor positions the query).
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.next == null || current.loadingMore) return;
    state = AsyncData(AuditHistoryState(items: current.items, next: current.next, loadingMore: true));
    try {
      final page = await _guard(
        () => ref.read(logbookRepositoryProvider).listAudit(type: type, objectId: objectId, cursor: current.next),
      );
      state = AsyncData(AuditHistoryState(items: [...current.items, ...page.items], next: page.next));
    } on ApiError catch (error) {
      state = AsyncData(AuditHistoryState(items: current.items, next: current.next, moreError: error));
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
