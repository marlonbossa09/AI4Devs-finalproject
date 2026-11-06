import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
import 'logbook_repository.dart';

part 'activity_detail.g.dart';

/// One activity with its plannings and progress history (M2-07), exactly as the server holds it.
/// A reload after any write goes through the API again; nothing is kept on the client.
@riverpod
Future<ActivityDetail> activityDetail(Ref ref, String id) async {
  try {
    return await ref.watch(logbookRepositoryProvider).getActivity(id);
  } on ApiError catch (error) {
    // If the server no longer recognizes the session, the app goes back to the login.
    if (error.isNotSignedIn) ref.read(authProvider.notifier).expired();
    rethrow;
  }
}
