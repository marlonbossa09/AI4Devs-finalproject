import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/audit_entities.dart';
import '../../domain/entities/logbook_entities.dart';
import 'side_panel.dart';
import 'unsaved_changes.dart';

part 'navigation.g.dart';

/// Pages of the signed-in area.
enum AppPage {
  dashboard,
  logbook,
  planning,
  progress,
  activities,
  activityDetail,
  continuation,
  reactivation,
  correction,
  audit,
  team,
  supervision,
  supervisionActivity,
  individualReport,
  teamReport,
}

/// Page being shown. It goes back to the dashboard with every new session.
@Riverpod(keepAlive: true)
class CurrentPage extends _$CurrentPage {
  @override
  AppPage build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return AppPage.dashboard;
  }

  /// Changes the page. If the summary editor holds unsaved text, the user is asked first (the change
  /// waits for their decision), so no way of leaving Mi bitácora loses text silently.
  void go(AppPage page) {
    if (page == state) return;
    ref.read(leaveRequestProvider.notifier).request(() {
      // A side panel belongs to the page it was opened from: it closes with it (the user has already decided about unsaved text).
      ref.read(sidePanelProvider.notifier).closeNow();
      state = page;
    });
  }
}

/// The activity chosen to record a progress entry on, and the page to return to afterwards.
class ProgressTargetState {
  const ProgressTargetState({required this.activity, this.back = AppPage.logbook});

  final ActivitySummary activity;
  final AppPage back;
}

/// Activity chosen to record a progress entry on (null = none yet). It is cleared with every new
/// session, like the page.
@Riverpod(keepAlive: true)
class ProgressTarget extends _$ProgressTarget {
  @override
  ProgressTargetState? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void select(ActivitySummary activity, {AppPage back = AppPage.logbook}) =>
      state = ProgressTargetState(activity: activity, back: back);
}

/// The activity chosen to plan a continuation of, and the page to return to afterwards.
class ContinuationTargetState {
  const ContinuationTargetState({required this.activity, this.back = AppPage.logbook});

  final ActivitySummary activity;
  final AppPage back;
}

/// Activity chosen to plan a continuation of (null = none yet). It is cleared with every new session.
@Riverpod(keepAlive: true)
class ContinuationTarget extends _$ContinuationTarget {
  @override
  ContinuationTargetState? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void select(ActivitySummary activity, {AppPage back = AppPage.logbook}) =>
      state = ContinuationTargetState(activity: activity, back: back);
}

/// The Completada activity chosen to reactivate (M3-04), and the page to return to afterwards.
class ReactivationTargetState {
  const ReactivationTargetState({required this.activity, this.back = AppPage.logbook});

  final ActivitySummary activity;
  final AppPage back;
}

/// Activity chosen to reactivate (null = none yet). It is cleared with every new session.
@Riverpod(keepAlive: true)
class ReactivationTarget extends _$ReactivationTarget {
  @override
  ReactivationTargetState? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void select(ActivitySummary activity, {AppPage back = AppPage.logbook}) =>
      state = ReactivationTargetState(activity: activity, back: back);
}

/// The progress entry chosen to correct (M3-03): its activity, the entry and the page to return to.
class CorrectionTargetState {
  const CorrectionTargetState({required this.activityId, required this.progressId, this.back = AppPage.activityDetail});

  final String activityId;
  final String progressId;
  final AppPage back;
}

/// Entry chosen to correct (null = none yet). It is cleared with every new session.
@Riverpod(keepAlive: true)
class CorrectionTarget extends _$CorrectionTarget {
  @override
  CorrectionTargetState? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void select({required String activityId, required String progressId, AppPage back = AppPage.activityDetail}) =>
      state = CorrectionTargetState(activityId: activityId, progressId: progressId, back: back);
}

/// The record whose audit is shown (M3-07), what to call it on screen and the page to return to.
class AuditTargetState {
  const AuditTargetState({
    required this.type,
    required this.objectId,
    required this.title,
    this.back = AppPage.logbook,
  });

  final AuditObjectType type;
  final String objectId;

  /// How the record is named on the audit screen (the day, the activity, the entry).
  final String title;
  final AppPage back;
}

/// Record chosen to consult the audit of (null = none yet). It is cleared with every new session.
@Riverpod(keepAlive: true)
class AuditTarget extends _$AuditTarget {
  @override
  AuditTargetState? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void select({
    required AuditObjectType type,
    required String objectId,
    required String title,
    AppPage back = AppPage.logbook,
  }) => state = AuditTargetState(type: type, objectId: objectId, title: title, back: back);
}

/// The activity whose detail is open, and the page that opened it (the "back" destination).
class OpenedActivity {
  const OpenedActivity({required this.id, required this.back});

  final String id;
  final AppPage back;
}

@Riverpod(keepAlive: true)
class ActivityNav extends _$ActivityNav {
  @override
  OpenedActivity? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void open(String id, {required AppPage back}) => state = OpenedActivity(id: id, back: back);
}
