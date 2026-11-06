import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../domain/entities/session.dart';
import 'auth_repository.dart';

part 'auth.g.dart';

/// Current session of the app: `null` means nobody is signed in.
@Riverpod(keepAlive: true)
class Auth extends _$Auth {
  @override
  Future<Session?> build() => ref.watch(authRepositoryProvider).getSession();

  /// Signs in. On failure the state is unchanged and the error is rethrown so the form can show
  /// its message.
  Future<void> login({required String user, required String password}) async {
    final session = await ref.read(authRepositoryProvider).login(user: user, password: password);
    state = AsyncData(session);
  }

  Future<void> logout() async {
    try {
      await ref.read(authRepositoryProvider).logout();
    } finally {
      state = const AsyncData(null);
    }
  }

  /// The server no longer recognizes the session (expired or revoked): back to the login.
  void expired() => state = const AsyncData(null);
}
