import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../auth/presentation/providers/auth.dart';

part 'navigation.g.dart';

/// Pages of the signed-in area.
enum AppPage { dashboard, logbook, planning }

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
