// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'activity_detail.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// One activity with its plannings and progress history (M2-07), exactly as the server holds it.
/// A reload after any write goes through the API again; nothing is kept on the client.

@ProviderFor(activityDetail)
const activityDetailProvider = ActivityDetailFamily._();

/// One activity with its plannings and progress history (M2-07), exactly as the server holds it.
/// A reload after any write goes through the API again; nothing is kept on the client.

final class ActivityDetailProvider
    extends
        $FunctionalProvider<
          AsyncValue<ActivityDetail>,
          ActivityDetail,
          FutureOr<ActivityDetail>
        >
    with $FutureModifier<ActivityDetail>, $FutureProvider<ActivityDetail> {
  /// One activity with its plannings and progress history (M2-07), exactly as the server holds it.
  /// A reload after any write goes through the API again; nothing is kept on the client.
  const ActivityDetailProvider._({
    required ActivityDetailFamily super.from,
    required String super.argument,
  }) : super(
         retry: null,
         name: r'activityDetailProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$activityDetailHash();

  @override
  String toString() {
    return r'activityDetailProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  $FutureProviderElement<ActivityDetail> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<ActivityDetail> create(Ref ref) {
    final argument = this.argument as String;
    return activityDetail(ref, argument);
  }

  @override
  bool operator ==(Object other) {
    return other is ActivityDetailProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$activityDetailHash() => r'1cb8d000bf768e33bca03adf26f64e16e4c46285';

/// One activity with its plannings and progress history (M2-07), exactly as the server holds it.
/// A reload after any write goes through the API again; nothing is kept on the client.

final class ActivityDetailFamily extends $Family
    with $FunctionalFamilyOverride<FutureOr<ActivityDetail>, String> {
  const ActivityDetailFamily._()
    : super(
        retry: null,
        name: r'activityDetailProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// One activity with its plannings and progress history (M2-07), exactly as the server holds it.
  /// A reload after any write goes through the API again; nothing is kept on the client.

  ActivityDetailProvider call(String id) =>
      ActivityDetailProvider._(argument: id, from: this);

  @override
  String toString() => r'activityDetailProvider';
}
