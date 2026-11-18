// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'report_generation.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// The individual report (M5-01). The user's own, or, for a supervisor, one of their team (the server decides: a 403 or a
/// 404 is its answer and the screen says so).

@ProviderFor(IndividualReportController)
const individualReportControllerProvider =
    IndividualReportControllerProvider._();

/// The individual report (M5-01). The user's own, or, for a supervisor, one of their team (the server decides: a 403 or a
/// 404 is its answer and the screen says so).
final class IndividualReportControllerProvider
    extends
        $NotifierProvider<
          IndividualReportController,
          ReportState<IndividualReport>
        > {
  /// The individual report (M5-01). The user's own, or, for a supervisor, one of their team (the server decides: a 403 or a
  /// 404 is its answer and the screen says so).
  const IndividualReportControllerProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'individualReportControllerProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$individualReportControllerHash();

  @$internal
  @override
  IndividualReportController create() => IndividualReportController();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ReportState<IndividualReport> value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ReportState<IndividualReport>>(
        value,
      ),
    );
  }
}

String _$individualReportControllerHash() =>
    r'4e459cfec4b02bbc01c2369ca59abb9739d12d14';

/// The individual report (M5-01). The user's own, or, for a supervisor, one of their team (the server decides: a 403 or a
/// 404 is its answer and the screen says so).

abstract class _$IndividualReportController
    extends $Notifier<ReportState<IndividualReport>> {
  ReportState<IndividualReport> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref
            as $Ref<
              ReportState<IndividualReport>,
              ReportState<IndividualReport>
            >;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<
                ReportState<IndividualReport>,
                ReportState<IndividualReport>
              >,
              ReportState<IndividualReport>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// The team report (M5-02), only for a supervisor with effective access.

@ProviderFor(TeamReportController)
const teamReportControllerProvider = TeamReportControllerProvider._();

/// The team report (M5-02), only for a supervisor with effective access.
final class TeamReportControllerProvider
    extends $NotifierProvider<TeamReportController, ReportState<TeamReport>> {
  /// The team report (M5-02), only for a supervisor with effective access.
  const TeamReportControllerProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'teamReportControllerProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$teamReportControllerHash();

  @$internal
  @override
  TeamReportController create() => TeamReportController();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ReportState<TeamReport> value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ReportState<TeamReport>>(value),
    );
  }
}

String _$teamReportControllerHash() =>
    r'10a522c510cf700f7b3eb5b9de262e1ff10136ef';

/// The team report (M5-02), only for a supervisor with effective access.

abstract class _$TeamReportController
    extends $Notifier<ReportState<TeamReport>> {
  ReportState<TeamReport> build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref =
        this.ref as $Ref<ReportState<TeamReport>, ReportState<TeamReport>>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ReportState<TeamReport>, ReportState<TeamReport>>,
              ReportState<TeamReport>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
