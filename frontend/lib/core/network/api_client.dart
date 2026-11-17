import 'package:dio/dio.dart';

import '../../config/app_config.dart';
import '../errors/api_error.dart';

/// HTTP client of the API (Dio).
///
/// - Sends the browser session cookie (`withCredentials`). The cookie is HttpOnly, so this code
///   never reads it.
/// - Adds the CSRF token (kept in memory only, never persisted) to every request that modifies.
class ApiClient {
  ApiClient({Dio? dio}) : dio = dio ?? _buildDio() {
    this.dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = csrf;
          final modifies = options.method != 'GET' && options.method != 'HEAD';
          if (modifies && token != null) {
            options.headers['X-CSRF-Token'] = token;
          }
          handler.next(options);
        },
      ),
    );
  }

  final Dio dio;

  /// CSRF token of the current session. Only in memory.
  String? csrf;

  static Dio _buildDio() => Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      contentType: Headers.jsonContentType,
      responseType: ResponseType.json,
      extra: {'withCredentials': true},
    ),
  );

  /// Request options for a non-repeatable operation (T-04): the key identifies ONE intention.
  Options withKey(String key) => Options(headers: {'Idempotency-Key': key});

  /// Runs [call] and converts any transport or API error into an [ApiError].
  Future<T> guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on DioException catch (error) {
      throw errorFromDio(error);
    }
  }
}

ApiError errorFromDio(DioException error) {
  final response = error.response;
  final data = response?.data;
  if (response != null && data is Map<String, dynamic> && data['codigo'] is String) {
    final rawDetails = data['detalles'];
    final details = rawDetails is List
        ? rawDetails.whereType<Map<String, dynamic>>().toList()
        : const <Map<String, dynamic>>[];
    return ApiError(
      code: data['codigo'] as String,
      message: (data['mensaje'] as String?) ?? '',
      details: details,
      status: response.statusCode,
      retryAfterSeconds: _retryAfterSeconds(response.headers.value('retry-after'), details),
    );
  }
  if (response == null) {
    return const ApiError(code: ApiError.network, message: 'Sin conexión');
  }
  return ApiError(
    code: ApiError.unknown,
    message: 'Respuesta inesperada',
    status: response.statusCode,
  );
}

/// Longest wait the client will honour: the server never asks for more than an hour, so anything above a
/// day is a malformed value, not a wait.
const int _maxRetryAfterSeconds = 24 * 60 * 60;

/// Seconds to wait from the `Retry-After` header (delay-seconds form), or from the `espera_segundos` detail
/// the server repeats in the body (the header is not readable by a cross-origin client unless exposed).
/// Anything that is not a positive whole number of seconds is ignored.
int? _retryAfterSeconds(String? header, List<Map<String, dynamic>> details) {
  int? valid(Object? raw) {
    final seconds = raw is int ? raw : (raw is String ? int.tryParse(raw.trim()) : null);
    return seconds != null && seconds > 0 && seconds <= _maxRetryAfterSeconds ? seconds : null;
  }

  final fromHeader = valid(header);
  if (fromHeader != null) return fromHeader;
  for (final detail in details) {
    final fromBody = valid(detail['espera_segundos']);
    if (fromBody != null) return fromBody;
  }
  return null;
}
