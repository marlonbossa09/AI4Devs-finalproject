import 'dart:math';

final Random _random = Random.secure();

/// Opaque, random key (128 bits, hex) that identifies ONE intention of a non-repeatable
/// operation. The same key is reused when retrying that intention (T-04).
String newKey() {
  final bytes = List<int>.generate(16, (_) => _random.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}
