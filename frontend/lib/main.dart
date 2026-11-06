import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';

/// Riverpod 3 retries failed providers automatically. Here a failure is shown to the person
/// (and retried by them), never repeated silently against the API.
Duration? noAutomaticRetry(int retryCount, Object error) => null;

void main() {
  runApp(const ProviderScope(retry: noAutomaticRetry, child: SmartworkApp()));
}
