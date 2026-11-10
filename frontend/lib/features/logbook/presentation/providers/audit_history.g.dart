// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'audit_history.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
/// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.

@ProviderFor(AuditHistory)
const auditHistoryProvider = AuditHistoryFamily._();

/// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
/// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.
final class AuditHistoryProvider
    extends $AsyncNotifierProvider<AuditHistory, AuditHistoryState> {
  /// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
  /// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.
  const AuditHistoryProvider._({
    required AuditHistoryFamily super.from,
    required (AuditObjectType, String) super.argument,
  }) : super(
         retry: null,
         name: r'auditHistoryProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$auditHistoryHash();

  @override
  String toString() {
    return r'auditHistoryProvider'
        ''
        '$argument';
  }

  @$internal
  @override
  AuditHistory create() => AuditHistory();

  @override
  bool operator ==(Object other) {
    return other is AuditHistoryProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$auditHistoryHash() => r'b8df86366dce4f8641b38af9a0e8ca0c067ffb3c';

/// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
/// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.

final class AuditHistoryFamily extends $Family
    with
        $ClassFamilyOverride<
          AuditHistory,
          AsyncValue<AuditHistoryState>,
          AuditHistoryState,
          FutureOr<AuditHistoryState>,
          (AuditObjectType, String)
        > {
  const AuditHistoryFamily._()
    : super(
        retry: null,
        name: r'auditHistoryProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
  /// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.

  AuditHistoryProvider call(AuditObjectType type, String objectId) =>
      AuditHistoryProvider._(argument: (type, objectId), from: this);

  @override
  String toString() => r'auditHistoryProvider';
}

/// The audit of ONE record (M3-07), one page at a time. It is read-only and is loaded again every time the screen
/// opens, so what it shows is what the server holds now. A failure to load more keeps the pages already shown.

abstract class _$AuditHistory extends $AsyncNotifier<AuditHistoryState> {
  late final _$args = ref.$arg as (AuditObjectType, String);
  AuditObjectType get type => _$args.$1;
  String get objectId => _$args.$2;

  FutureOr<AuditHistoryState> build(AuditObjectType type, String objectId);
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build(_$args.$1, _$args.$2);
    final ref =
        this.ref as $Ref<AsyncValue<AuditHistoryState>, AuditHistoryState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<AuditHistoryState>, AuditHistoryState>,
              AsyncValue<AuditHistoryState>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
