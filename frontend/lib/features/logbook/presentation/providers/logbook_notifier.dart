import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
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
