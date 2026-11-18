// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'supervision_data.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
/// never defaulted by the client. It lives only in memory and is dropped with the session.

@ProviderFor(SupervisionFeed)
const supervisionFeedProvider = SupervisionFeedFamily._();

/// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
/// never defaulted by the client. It lives only in memory and is dropped with the session.
final class SupervisionFeedProvider
    extends $AsyncNotifierProvider<SupervisionFeed, SupervisionFeedState> {
  /// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
  /// never defaulted by the client. It lives only in memory and is dropped with the session.
  const SupervisionFeedProvider._({
    required SupervisionFeedFamily super.from,
    required (DateTime, DateTime) super.argument,
  }) : super(
         retry: null,
         name: r'supervisionFeedProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$supervisionFeedHash();

  @override
  String toString() {
    return r'supervisionFeedProvider'
        ''
        '$argument';
  }

  @$internal
  @override
  SupervisionFeed create() => SupervisionFeed();

  @override
  bool operator ==(Object other) {
    return other is SupervisionFeedProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$supervisionFeedHash() => r'4385259dac324ce19de3d0d07d4f1021274de3ac';

/// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
/// never defaulted by the client. It lives only in memory and is dropped with the session.

final class SupervisionFeedFamily extends $Family
    with
        $ClassFamilyOverride<
          SupervisionFeed,
          AsyncValue<SupervisionFeedState>,
          SupervisionFeedState,
          FutureOr<SupervisionFeedState>,
          (DateTime, DateTime)
        > {
  const SupervisionFeedFamily._()
    : super(
        retry: null,
        name: r'supervisionFeedProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
  /// never defaulted by the client. It lives only in memory and is dropped with the session.

  SupervisionFeedProvider call(DateTime from, DateTime to) =>
      SupervisionFeedProvider._(argument: (from, to), from: this);

  @override
  String toString() => r'supervisionFeedProvider';
}

/// The supervision view (M4-03) for ONE period, one page at a time. The period is part of the key: it is always sent,
/// never defaulted by the client. It lives only in memory and is dropped with the session.

abstract class _$SupervisionFeed extends $AsyncNotifier<SupervisionFeedState> {
  late final _$args = ref.$arg as (DateTime, DateTime);
  DateTime get from => _$args.$1;
  DateTime get to => _$args.$2;

  FutureOr<SupervisionFeedState> build(DateTime from, DateTime to);
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build(_$args.$1, _$args.$2);
    final ref =
        this.ref
            as $Ref<AsyncValue<SupervisionFeedState>, SupervisionFeedState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<
                AsyncValue<SupervisionFeedState>,
                SupervisionFeedState
              >,
              AsyncValue<SupervisionFeedState>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// The history of one activity (M4-04). `null` = not available (missing, or not readable: the server does not say which).

@ProviderFor(activityHistory)
const activityHistoryProvider = ActivityHistoryFamily._();

/// The history of one activity (M4-04). `null` = not available (missing, or not readable: the server does not say which).

final class ActivityHistoryProvider
    extends
        $FunctionalProvider<
          AsyncValue<ActivityHistory?>,
          ActivityHistory?,
          FutureOr<ActivityHistory?>
        >
    with $FutureModifier<ActivityHistory?>, $FutureProvider<ActivityHistory?> {
  /// The history of one activity (M4-04). `null` = not available (missing, or not readable: the server does not say which).
  const ActivityHistoryProvider._({
    required ActivityHistoryFamily super.from,
    required String super.argument,
  }) : super(
         retry: null,
         name: r'activityHistoryProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$activityHistoryHash();

  @override
  String toString() {
    return r'activityHistoryProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  $FutureProviderElement<ActivityHistory?> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<ActivityHistory?> create(Ref ref) {
    final argument = this.argument as String;
    return activityHistory(ref, argument);
  }

  @override
  bool operator ==(Object other) {
    return other is ActivityHistoryProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$activityHistoryHash() => r'f8e6ec468814b89e5c1888114578ea1386f840b0';

/// The history of one activity (M4-04). `null` = not available (missing, or not readable: the server does not say which).

final class ActivityHistoryFamily extends $Family
    with $FunctionalFamilyOverride<FutureOr<ActivityHistory?>, String> {
  const ActivityHistoryFamily._()
    : super(
        retry: null,
        name: r'activityHistoryProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// The history of one activity (M4-04). `null` = not available (missing, or not readable: the server does not say which).

  ActivityHistoryProvider call(String activityId) =>
      ActivityHistoryProvider._(argument: activityId, from: this);

  @override
  String toString() => r'activityHistoryProvider';
}
