import 'dart:math';

final Random _random = Random.secure();

/// Opaque, random key (128 bits, hex) that identifies ONE intention of a non-repeatable
/// operation. The same key is reused when retrying that intention (T-04).
String newKey() {
  final bytes = List<int>.generate(16, (_) => _random.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

/// The idempotency key of ONE intention of the user (T-04).
///
/// - Retrying the same request (same [fingerprint]) reuses the key, so the server never repeats
///   the effect.
/// - Changing what is sent is a different intention: it gets a new key.
/// - After the server accepts the request, [accepted] ends the intention; the next one is new.
class IntentionKey {
  String? _key;
  String? _fingerprint;

  /// The key for a request whose content is summarized by [fingerprint].
  String forRequest(String fingerprint) {
    if (_key == null || _fingerprint != fingerprint) {
      _key = newKey();
      _fingerprint = fingerprint;
    }
    return _key!;
  }

  /// The server accepted the request: the next one is a new intention.
  void accepted() {
    _key = null;
    _fingerprint = null;
  }
}
