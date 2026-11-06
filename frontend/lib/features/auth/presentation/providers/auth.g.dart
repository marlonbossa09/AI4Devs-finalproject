// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auth.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Current session of the app: `null` means nobody is signed in.

@ProviderFor(Auth)
const authProvider = AuthProvider._();

/// Current session of the app: `null` means nobody is signed in.
final class AuthProvider extends $AsyncNotifierProvider<Auth, Session?> {
  /// Current session of the app: `null` means nobody is signed in.
  const AuthProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'authProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$authHash();

  @$internal
  @override
  Auth create() => Auth();
}

String _$authHash() => r'facad8e93a50c9d6657367cd75d160113bf797c5';

/// Current session of the app: `null` means nobody is signed in.

abstract class _$Auth extends $AsyncNotifier<Session?> {
  FutureOr<Session?> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<AsyncValue<Session?>, Session?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<Session?>, Session?>,
              AsyncValue<Session?>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
