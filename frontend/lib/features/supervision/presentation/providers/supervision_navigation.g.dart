// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'supervision_navigation.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(SupervisionSelection)
const supervisionSelectionProvider = SupervisionSelectionProvider._();

final class SupervisionSelectionProvider
    extends $NotifierProvider<SupervisionSelection, SupervisionSelectionState> {
  const SupervisionSelectionProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'supervisionSelectionProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$supervisionSelectionHash();

  @$internal
  @override
  SupervisionSelection create() => SupervisionSelection();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SupervisionSelectionState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<SupervisionSelectionState>(value),
    );
  }
}

String _$supervisionSelectionHash() =>
    r'b07ef5e78cbb3f3ee9b1f9ef0d957ab0babc7824';

abstract class _$SupervisionSelection
    extends $Notifier<SupervisionSelectionState> {
  SupervisionSelectionState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref as $Ref<SupervisionSelectionState, SupervisionSelectionState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<SupervisionSelectionState, SupervisionSelectionState>,
              SupervisionSelectionState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

@ProviderFor(SupervisionActivityTarget)
const supervisionActivityTargetProvider = SupervisionActivityTargetProvider._();

final class SupervisionActivityTargetProvider
    extends
        $NotifierProvider<
          SupervisionActivityTarget,
          SupervisionActivityTargetState?
        > {
  const SupervisionActivityTargetProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'supervisionActivityTargetProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$supervisionActivityTargetHash();

  @$internal
  @override
  SupervisionActivityTarget create() => SupervisionActivityTarget();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SupervisionActivityTargetState? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<SupervisionActivityTargetState?>(
        value,
      ),
    );
  }
}

String _$supervisionActivityTargetHash() =>
    r'0e3ad191771be7832ea19c89e7a8630beaab0919';

abstract class _$SupervisionActivityTarget
    extends $Notifier<SupervisionActivityTargetState?> {
  SupervisionActivityTargetState? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref
            as $Ref<
              SupervisionActivityTargetState?,
              SupervisionActivityTargetState?
            >;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<
                SupervisionActivityTargetState?,
                SupervisionActivityTargetState?
              >,
              SupervisionActivityTargetState?,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
