import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
import 'activity_detail.dart';
import 'activity_list.dart';
import 'logbook_repository.dart';

part 'logbook_notifier.g.dart';

/// What is persisted for one date. `null` means there is no logbook for it.
///
/// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
/// persisted, not what the client assumes.
@riverpod
class LogbookNotifier extends _$LogbookNotifier {
  @override
  Future<LogbookDay?> build(DateTime date) {
    return _guard(() => ref.watch(logbookRepositoryProvider).getLogbook(date));
  }

  /// Opens the logbook of the date (M2-01b).
  Future<OpenResult> open() async {
    final result = await _guard(() => ref.read(logbookRepositoryProvider).openLogbook(date));
    await _reload();
    return result;
  }

  /// Creates a planned activity (M2-03). Throws `ApiError` when the server rejects it.
  Future<PlanResult> createActivity({
    required String title,
    String? description,
    required String key,
  }) async {
    final result = await _guard(
      () => ref.read(logbookRepositoryProvider).createActivity(
        date: date,
        title: title,
        description: description,
        key: key,
      ),
    );
    await _reload();
    return result;
  }

  /// Records a progress entry (M2-05) on [activityId] for this notifier date. Throws `ApiError`
  /// when the server rejects it.
  ///
  /// The server recalculates the activity status, and that status is visible in every day where
  /// the activity appears (and in the indicators built from it), so ALL cached days, and the
  /// activity detail and list, are reloaded from the API, not only this one.
  Future<ProgressResult> registerProgress({
    required String activityId,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final result = await _guard(
      () => ref.read(logbookRepositoryProvider).registerProgress(
        activityId: activityId,
        date: date,
        status: status,
        description: description,
        blockReason: blockReason,
        key: key,
      ),
    );
    await _reloadEverything();
    return result;
  }

  /// Records work that was not planned (M2-06) for this notifier date: the activity and its first
  /// progress entry are created by ONE server operation. Throws `ApiError` when the server rejects it.
  Future<ProgressResult> registerUnplanned({
    required String title,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final result = await _guard(
      () => ref.read(logbookRepositoryProvider).registerUnplanned(
        date: date,
        title: title,
        status: status,
        description: description,
        blockReason: blockReason,
        key: key,
      ),
    );
    await _reloadEverything();
    return result;
  }

  /// A new activity or progress entry changes what EVERY cached day, the activity list and any open
  /// detail show (status, indicators, history), so all of them are reloaded from the API.
  Future<void> _reloadEverything() async {
    ref.invalidate(logbookProvider);
    ref.invalidate(activityDetailProvider);
    ref.invalidate(activityListProvider);
    await future;
  }

  Future<void> _reload() async {
    ref.invalidateSelf();
    await future;
  }

  /// If the server no longer recognizes the session, the app goes back to the login.
  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on ApiError catch (error) {
      if (error.isNotSignedIn) {
        ref.read(authProvider.notifier).expired();
      }
      rethrow;
    }
  }
}
