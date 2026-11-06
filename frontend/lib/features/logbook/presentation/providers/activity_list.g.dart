// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'activity_list.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Statuses the activity list is filtered by (empty = all). It filters by CURRENT status (M2-08).

@ProviderFor(ActivityFilter)
const activityFilterProvider = ActivityFilterProvider._();

/// Statuses the activity list is filtered by (empty = all). It filters by CURRENT status (M2-08).
final class ActivityFilterProvider
    extends $NotifierProvider<ActivityFilter, Set<ActivityStatus>> {
  /// Statuses the activity list is filtered by (empty = all). It filters by CURRENT status (M2-08).
  const ActivityFilterProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'activityFilterProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$activityFilterHash();

  @$internal
  @override
  ActivityFilter create() => ActivityFilter();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(Set<ActivityStatus> value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<Set<ActivityStatus>>(value),
    );
  }
}

String _$activityFilterHash() => r'5cb1b3b37c54b257af3907f528ff400bcfc5ef7e';

/// Statuses the activity list is filtered by (empty = all). It filters by CURRENT status (M2-08).

abstract class _$ActivityFilter extends $Notifier<Set<ActivityStatus>> {
  Set<ActivityStatus> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<Set<ActivityStatus>, Set<ActivityStatus>>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<Set<ActivityStatus>, Set<ActivityStatus>>,
              Set<ActivityStatus>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// The user's activities (M2-08), newest first, one page at a time. Changing the filter starts
/// again from the first page.

@ProviderFor(ActivityList)
const activityListProvider = ActivityListProvider._();

/// The user's activities (M2-08), newest first, one page at a time. Changing the filter starts
/// again from the first page.
final class ActivityListProvider
    extends $AsyncNotifierProvider<ActivityList, ActivityListState> {
  /// The user's activities (M2-08), newest first, one page at a time. Changing the filter starts
  /// again from the first page.
  const ActivityListProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'activityListProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$activityListHash();

  @$internal
  @override
  ActivityList create() => ActivityList();
}

String _$activityListHash() => r'930e62c666c8d0cbe843fe69fd0257db87488b4f';

/// The user's activities (M2-08), newest first, one page at a time. Changing the filter starts
/// again from the first page.

abstract class _$ActivityList extends $AsyncNotifier<ActivityListState> {
  FutureOr<ActivityListState> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref as $Ref<AsyncValue<ActivityListState>, ActivityListState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<ActivityListState>, ActivityListState>,
              AsyncValue<ActivityListState>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
