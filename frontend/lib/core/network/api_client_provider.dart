import 'package:riverpod_annotation/riverpod_annotation.dart';

import 'api_client.dart';

part 'api_client_provider.g.dart';

/// One client for the whole app: it holds the in-memory CSRF token of the session.
@Riverpod(keepAlive: true)
ApiClient apiClient(Ref ref) => ApiClient();
