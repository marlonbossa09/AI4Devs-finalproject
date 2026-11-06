/// Static configuration of the client.
///
/// The API base URL is injected at build/run time:
///   flutter run -d chrome --web-port 8080 --dart-define=API_BASE_URL=http://localhost:8000
/// When empty (default), the client talks to its own origin. That is the demo setup, where
/// FastAPI serves the compiled client and the API from the same origin (ADR-002).
class AppConfig {
  const AppConfig._();

  static const String apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String apiPrefix = '/api/v1';
}
