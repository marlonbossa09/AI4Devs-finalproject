// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'team_data.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// The current members of the user's team (M4-05), every page, as the server orders them (name, id). It lives only
/// in memory and is dropped with the session; it is never written to any storage.

@ProviderFor(teamMembers)
const teamMembersProvider = TeamMembersProvider._();

/// The current members of the user's team (M4-05), every page, as the server orders them (name, id). It lives only
/// in memory and is dropped with the session; it is never written to any storage.

final class TeamMembersProvider
    extends
        $FunctionalProvider<
          AsyncValue<List<TeamMember>>,
          List<TeamMember>,
          FutureOr<List<TeamMember>>
        >
    with $FutureModifier<List<TeamMember>>, $FutureProvider<List<TeamMember>> {
  /// The current members of the user's team (M4-05), every page, as the server orders them (name, id). It lives only
  /// in memory and is dropped with the session; it is never written to any storage.
  const TeamMembersProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'teamMembersProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$teamMembersHash();

  @$internal
  @override
  $FutureProviderElement<List<TeamMember>> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<List<TeamMember>> create(Ref ref) {
    return teamMembers(ref);
  }
}

String _$teamMembersHash() => r'fb508f5743fd557fc08f8a21d49ffdc889573885';

/// The logbook of a colleague for one date (M4-01), read-only. `null` = not available (no logbook, or none the user may
/// read: the server does not say which).

@ProviderFor(peerLogbook)
const peerLogbookProvider = PeerLogbookFamily._();

/// The logbook of a colleague for one date (M4-01), read-only. `null` = not available (no logbook, or none the user may
/// read: the server does not say which).

final class PeerLogbookProvider
    extends
        $FunctionalProvider<
          AsyncValue<PeerLogbook?>,
          PeerLogbook?,
          FutureOr<PeerLogbook?>
        >
    with $FutureModifier<PeerLogbook?>, $FutureProvider<PeerLogbook?> {
  /// The logbook of a colleague for one date (M4-01), read-only. `null` = not available (no logbook, or none the user may
  /// read: the server does not say which).
  const PeerLogbookProvider._({
    required PeerLogbookFamily super.from,
    required (String, DateTime) super.argument,
  }) : super(
         retry: null,
         name: r'peerLogbookProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$peerLogbookHash();

  @override
  String toString() {
    return r'peerLogbookProvider'
        ''
        '$argument';
  }

  @$internal
  @override
  $FutureProviderElement<PeerLogbook?> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<PeerLogbook?> create(Ref ref) {
    final argument = this.argument as (String, DateTime);
    return peerLogbook(ref, argument.$1, argument.$2);
  }

  @override
  bool operator ==(Object other) {
    return other is PeerLogbookProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$peerLogbookHash() => r'af7f6ae0f70326ce8439e6f4071c4eb39f301cca';

/// The logbook of a colleague for one date (M4-01), read-only. `null` = not available (no logbook, or none the user may
/// read: the server does not say which).

final class PeerLogbookFamily extends $Family
    with $FunctionalFamilyOverride<FutureOr<PeerLogbook?>, (String, DateTime)> {
  const PeerLogbookFamily._()
    : super(
        retry: null,
        name: r'peerLogbookProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// The logbook of a colleague for one date (M4-01), read-only. `null` = not available (no logbook, or none the user may
  /// read: the server does not say which).

  PeerLogbookProvider call(String personId, DateTime date) =>
      PeerLogbookProvider._(argument: (personId, date), from: this);

  @override
  String toString() => r'peerLogbookProvider';
}

/// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
/// always sent, never defaulted by the client.

@ProviderFor(HistoryView)
const historyViewProvider = HistoryViewFamily._();

/// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
/// always sent, never defaulted by the client.
final class HistoryViewProvider
    extends $AsyncNotifierProvider<HistoryView, HistoryViewState> {
  /// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
  /// always sent, never defaulted by the client.
  const HistoryViewProvider._({
    required HistoryViewFamily super.from,
    required (DateTime, DateTime, String?) super.argument,
  }) : super(
         retry: null,
         name: r'historyViewProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$historyViewHash();

  @override
  String toString() {
    return r'historyViewProvider'
        ''
        '$argument';
  }

  @$internal
  @override
  HistoryView create() => HistoryView();

  @override
  bool operator ==(Object other) {
    return other is HistoryViewProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$historyViewHash() => r'a9342d4a79673e0ac086525e6d4d5843b32e4b2b';

/// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
/// always sent, never defaulted by the client.

final class HistoryViewFamily extends $Family
    with
        $ClassFamilyOverride<
          HistoryView,
          AsyncValue<HistoryViewState>,
          HistoryViewState,
          FutureOr<HistoryViewState>,
          (DateTime, DateTime, String?)
        > {
  const HistoryViewFamily._()
    : super(
        retry: null,
        name: r'historyViewProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
  /// always sent, never defaulted by the client.

  HistoryViewProvider call(DateTime from, DateTime to, String? personId) =>
      HistoryViewProvider._(argument: (from, to, personId), from: this);

  @override
  String toString() => r'historyViewProvider';
}

/// The history for ONE range and an optional person (M4-02), one page at a time. The range is part of the key: it is
/// always sent, never defaulted by the client.

abstract class _$HistoryView extends $AsyncNotifier<HistoryViewState> {
  late final _$args = ref.$arg as (DateTime, DateTime, String?);
  DateTime get from => _$args.$1;
  DateTime get to => _$args.$2;
  String? get personId => _$args.$3;

  FutureOr<HistoryViewState> build(
    DateTime from,
    DateTime to,
    String? personId,
  );
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build(_$args.$1, _$args.$2, _$args.$3);
    final ref =
        this.ref as $Ref<AsyncValue<HistoryViewState>, HistoryViewState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<HistoryViewState>, HistoryViewState>,
              AsyncValue<HistoryViewState>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
