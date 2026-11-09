// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'navigation.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Page being shown. It goes back to the dashboard with every new session.

@ProviderFor(CurrentPage)
const currentPageProvider = CurrentPageProvider._();

/// Page being shown. It goes back to the dashboard with every new session.
final class CurrentPageProvider
    extends $NotifierProvider<CurrentPage, AppPage> {
  /// Page being shown. It goes back to the dashboard with every new session.
  const CurrentPageProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'currentPageProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$currentPageHash();

  @$internal
  @override
  CurrentPage create() => CurrentPage();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AppPage value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AppPage>(value),
    );
  }
}

String _$currentPageHash() => r'776a6d15c5d43e1851be52d79255585e6161c0bd';

/// Page being shown. It goes back to the dashboard with every new session.

abstract class _$CurrentPage extends $Notifier<AppPage> {
  AppPage build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<AppPage, AppPage>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AppPage, AppPage>,
              AppPage,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// Activity chosen to record a progress entry on (null = none yet). It is cleared with every new
/// session, like the page.

@ProviderFor(ProgressTarget)
const progressTargetProvider = ProgressTargetProvider._();

/// Activity chosen to record a progress entry on (null = none yet). It is cleared with every new
/// session, like the page.
final class ProgressTargetProvider
    extends $NotifierProvider<ProgressTarget, ProgressTargetState?> {
  /// Activity chosen to record a progress entry on (null = none yet). It is cleared with every new
  /// session, like the page.
  const ProgressTargetProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'progressTargetProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$progressTargetHash();

  @$internal
  @override
  ProgressTarget create() => ProgressTarget();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ProgressTargetState? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ProgressTargetState?>(value),
    );
  }
}

String _$progressTargetHash() => r'9a69eb04f9a9ec5ba7968e63e264250e50dab081';

/// Activity chosen to record a progress entry on (null = none yet). It is cleared with every new
/// session, like the page.

abstract class _$ProgressTarget extends $Notifier<ProgressTargetState?> {
  ProgressTargetState? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<ProgressTargetState?, ProgressTargetState?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ProgressTargetState?, ProgressTargetState?>,
              ProgressTargetState?,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// Activity chosen to plan a continuation of (null = none yet). It is cleared with every new session.

@ProviderFor(ContinuationTarget)
const continuationTargetProvider = ContinuationTargetProvider._();

/// Activity chosen to plan a continuation of (null = none yet). It is cleared with every new session.
final class ContinuationTargetProvider
    extends $NotifierProvider<ContinuationTarget, ContinuationTargetState?> {
  /// Activity chosen to plan a continuation of (null = none yet). It is cleared with every new session.
  const ContinuationTargetProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'continuationTargetProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$continuationTargetHash();

  @$internal
  @override
  ContinuationTarget create() => ContinuationTarget();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ContinuationTargetState? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ContinuationTargetState?>(value),
    );
  }
}

String _$continuationTargetHash() =>
    r'c40cc4e1a25c3e195898a3bb672740ccefd1e8bf';

/// Activity chosen to plan a continuation of (null = none yet). It is cleared with every new session.

abstract class _$ContinuationTarget
    extends $Notifier<ContinuationTargetState?> {
  ContinuationTargetState? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref as $Ref<ContinuationTargetState?, ContinuationTargetState?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ContinuationTargetState?, ContinuationTargetState?>,
              ContinuationTargetState?,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

@ProviderFor(ActivityNav)
const activityNavProvider = ActivityNavProvider._();

final class ActivityNavProvider
    extends $NotifierProvider<ActivityNav, OpenedActivity?> {
  const ActivityNavProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'activityNavProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$activityNavHash();

  @$internal
  @override
  ActivityNav create() => ActivityNav();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(OpenedActivity? value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<OpenedActivity?>(value),
    );
  }
}

String _$activityNavHash() => r'67913bad6d07e18c470c4ebb607fb9179b399c3d';

abstract class _$ActivityNav extends $Notifier<OpenedActivity?> {
  OpenedActivity? build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<OpenedActivity?, OpenedActivity?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<OpenedActivity?, OpenedActivity?>,
              OpenedActivity?,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
