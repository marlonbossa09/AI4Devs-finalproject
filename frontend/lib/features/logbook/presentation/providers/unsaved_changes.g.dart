// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'unsaved_changes.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(unsavedGuard)
const unsavedGuardProvider = UnsavedGuardProvider._();

final class UnsavedGuardProvider
    extends $FunctionalProvider<UnsavedGuard, UnsavedGuard, UnsavedGuard>
    with $Provider<UnsavedGuard> {
  const UnsavedGuardProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'unsavedGuardProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$unsavedGuardHash();

  @$internal
  @override
  $ProviderElement<UnsavedGuard> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  UnsavedGuard create(Ref ref) {
    return unsavedGuard(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(UnsavedGuard value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<UnsavedGuard>(value),
    );
  }
}

String _$unsavedGuardHash() => r'31520a159599af0c455b28844de387f07446fc99';

/// Every way of leaving the screen goes through [request]: it runs the action at once when nothing
/// would be lost, and otherwise holds it until the user chooses to discard the text or keep editing.

@ProviderFor(LeaveRequest)
const leaveRequestProvider = LeaveRequestProvider._();

/// Every way of leaving the screen goes through [request]: it runs the action at once when nothing
/// would be lost, and otherwise holds it until the user chooses to discard the text or keep editing.
final class LeaveRequestProvider
    extends $NotifierProvider<LeaveRequest, PendingLeave?> {
  /// Every way of leaving the screen goes through [request]: it runs the action at once when nothing
  /// would be lost, and otherwise holds it until the user chooses to discard the text or keep editing.
  const LeaveRequestProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'leaveRequestProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$leaveRequestHash();

  @$internal
  @override
  LeaveRequest create() => LeaveRequest();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(PendingLeave? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<PendingLeave?>(value),
    );
  }
}

String _$leaveRequestHash() => r'0d88326338e1abe1077be292972e0b0f2b966517';

/// Every way of leaving the screen goes through [request]: it runs the action at once when nothing
/// would be lost, and otherwise holds it until the user chooses to discard the text or keep editing.

abstract class _$LeaveRequest extends $Notifier<PendingLeave?> {
  PendingLeave? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<PendingLeave?, PendingLeave?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<PendingLeave?, PendingLeave?>,
              PendingLeave?,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
