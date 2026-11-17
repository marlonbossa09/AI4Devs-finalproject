/// What a one-time code is for: the first access of a person without a password (M1-03b) or the recovery of one that
/// already has it (M1-09b). Both are issued by an operator and redeemed here.
enum AccessCodePurpose { firstAccess, recovery }

/// Contract of the redemption of one-time codes. Errors are thrown as `ApiError`.
///
/// Redeeming a code NEVER signs the person in (there is one single way to create a session: the login) and nothing about the code or the
/// password is kept by the client after the call.
abstract class AccessCodeRepository {
  Future<void> redeem(
    AccessCodePurpose purpose, {
    required String identifier,
    required String code,
    required String newPassword,
  });
}
