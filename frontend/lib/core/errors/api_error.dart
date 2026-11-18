/// An error reported by the API (stable `codigo`, human `mensaje`, optional `detalles`) or a
/// transport error. Framework-free: the domain and presentation layers only know this type.
class ApiError implements Exception {
  const ApiError({
    required this.code,
    required this.message,
    this.details = const [],
    this.status,
    this.retryAfterSeconds,
  });

  /// Stable code from the API catalog (e.g. `FECHA_NO_CUBIERTA`), or one of the local codes
  /// [network] / [unknown].
  final String code;
  final String message;
  final List<Map<String, dynamic>> details;

  /// HTTP status, when the server answered.
  final int? status;

  /// Seconds the server asks to wait before trying again (`Retry-After` of a 429, or the same value in
  /// the details). `null` when the server gave no valid, positive wait.
  final int? retryAfterSeconds;

  static const String network = 'RED';
  static const String unknown = 'ERROR_DESCONOCIDO';
  static const String notSignedIn = 'NO_IDENTIFICADA';
  static const String tooManyRequests = 'DEMASIADAS_SOLICITUDES';

  bool get isNotSignedIn => code == notSignedIn;

  /// What the server says about repeating the request (`reintento`, P-12): `true` only for a transient technical failure,
  /// `false` for everything else it classifies, and `null` when it says nothing. The two fields it sends (`reintento` and
  /// `motivo`) are read together and must agree; a contradictory answer counts as "says nothing" (never retry on doubt).
  bool? get retryAllowed {
    for (final detail in details) {
      if (detail['campo'] != 'reintento') continue;
      final flag = detail['reintento'];
      final reason = detail['motivo'];
      if (flag == true && reason == 'posible') return true;
      if (flag == false && reason == 'no_aplicable') return false;
      return null;
    }
    return null;
  }

  /// A temporary restriction on attempts (429): the client must wait [retryAfterSeconds].
  bool get isTooManyRequests => code == tooManyRequests;

  @override
  String toString() => 'ApiError($code, $status)';
}
