import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/errors/api_error.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/report_entities.dart';
import 'report_repository.dart';

part 'report_generation.g.dart';

/// Where a generation is: nothing asked yet, waiting for the server, a report ready, or failed. There is NO progress
/// figure: the server gives none, so the app shows that a generation is running but never how far along it is.
enum ReportPhase { idle, generating, ready, failed }

/// What a report screen shows. A report lives ONLY here, in memory: it is never written to any storage and it is dropped
/// when the screen is left, when the user changes or when the session ends.
class ReportState<T> {
  const ReportState._(this.phase, {this.report, this.error});

  const ReportState.idle() : this._(ReportPhase.idle);
  const ReportState.generating() : this._(ReportPhase.generating);
  const ReportState.ready(T report) : this._(ReportPhase.ready, report: report);
  const ReportState.failed(ApiError error) : this._(ReportPhase.failed, error: error);

  final ReportPhase phase;
  final T? report;
  final ApiError? error;

  bool get isGenerating => phase == ReportPhase.generating;
}

String? _signedInUser(Ref ref) => ref.read(authProvider).value?.user.id;

/// Runs one generation. Rules shared by both reports:
/// - ONE request per user action: while one is in flight a new one is ignored (no duplicates from repeated clicks);
/// - starting a request drops the report shown before, so a rejection (no longer authorized, a limit, a failure) never
///   leaves an earlier report on screen;
/// - the answer of a request made by ANOTHER session (the user left or changed meanwhile) is discarded, never shown;
/// - nothing is retried by itself: a retry is always a new action of the user.
Future<void> _run<T>(Ref ref, Future<T> Function() call, void Function(ReportState<T>) set, bool Function() isCurrent) async {
  final owner = _signedInUser(ref);
  set(ReportState<T>.generating());
  try {
    final report = await call();
    if (ref.mounted && isCurrent() && _signedInUser(ref) == owner) set(ReportState<T>.ready(report));
  } on ApiError catch (error) {
    if (!ref.mounted) return;
    if (error.isNotSignedIn) ref.read(authProvider.notifier).expired();
    if (isCurrent() && _signedInUser(ref) == owner) set(ReportState<T>.failed(error));
  } catch (_) {
    // An answer the app cannot read (it does not match the contract): a fixed error, never the content received.
    if (ref.mounted && isCurrent() && _signedInUser(ref) == owner) {
      set(ReportState<T>.failed(const ApiError(code: ApiError.unknown, message: '')));
    }
  }
}

/// The individual report (M5-01). The user's own, or, for a supervisor, one of their team (the server decides: a 403 or a
/// 404 is its answer and the screen says so).
@riverpod
class IndividualReportController extends _$IndividualReportController {
  @override
  ReportState<IndividualReport> build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return const ReportState.idle();
  }

  Future<void> generate({required DateTime from, required DateTime to, String? personId}) async {
    if (state.isGenerating) return;
    await _run<IndividualReport>(
      ref,
      () => ref.read(reportRepositoryProvider).generateIndividual(from: from, to: to, personId: personId),
      (value) => state = value,
      () => ref.mounted,
    );
  }

  /// Takes the report away (the user changed what to ask for). Ignored while a request is in flight.
  void clear() {
    if (!state.isGenerating && state.phase != ReportPhase.idle) state = const ReportState.idle();
  }
}

/// The team report (M5-02), only for a supervisor with effective access.
@riverpod
class TeamReportController extends _$TeamReportController {
  @override
  ReportState<TeamReport> build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return const ReportState.idle();
  }

  Future<void> generate({required DateTime from, required DateTime to}) async {
    if (state.isGenerating) return;
    await _run<TeamReport>(
      ref,
      () => ref.read(reportRepositoryProvider).generateTeam(from: from, to: to),
      (value) => state = value,
      () => ref.mounted,
    );
  }

  void clear() {
    if (!state.isGenerating && state.phase != ReportPhase.idle) state = const ReportState.idle();
  }
}
