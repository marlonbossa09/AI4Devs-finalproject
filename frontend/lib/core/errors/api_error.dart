/// An error reported by the API (stable `codigo`, human `mensaje`, optional `detalles`) or a
/// transport error. Framework-free: the domain and presentation layers only know this type.
class ApiError implements Exception {
  const ApiError({
    required this.code,
    required this.message,
    this.details = const [],
    this.status,
  });

  /// Stable code from the API catalog (e.g. `FECHA_NO_CUBIERTA`), or one of the local codes
  /// [network] / [unknown].
  final String code;
  final String message;
  final List<Map<String, dynamic>> details;

  /// HTTP status, when the server answered.
  final int? status;

  static const String network = 'RED';
  static const String unknown = 'ERROR_DESCONOCIDO';
  static const String notSignedIn = 'NO_IDENTIFICADA';

  bool get isNotSignedIn => code == notSignedIn;

  @override
  String toString() => 'ApiError($code, $status)';
}
