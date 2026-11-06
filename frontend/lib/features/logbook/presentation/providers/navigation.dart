import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';

part 'navigation.g.dart';

/// Pages of the signed-in area.
enum AppPage { dashboard, logbook, planning, progress, activities, activityDetail, unplanned }

/// Page being shown. It goes back to the dashboard with every new session.
@Riverpod(keepAlive: true)
class CurrentPage extends _$CurrentPage {
  @override
  AppPage build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return AppPage.dashboard;
  }

  void go(AppPage page) => state = page;
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
