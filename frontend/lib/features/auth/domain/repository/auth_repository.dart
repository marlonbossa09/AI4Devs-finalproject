import '../entities/session.dart';

/// Contract of the session operations (M1-01a/b/c). Errors are thrown as `ApiError`.
abstract class AuthRepository {
  /// Signs in and returns the resulting session.
  Future<Session> login({required String user, required String password});

  /// Returns the current session, or `null` when nobody is signed in.
  Future<Session?> getSession();

  /// Ends the session (it is revoked on the server).
  Future<void> logout();
}
