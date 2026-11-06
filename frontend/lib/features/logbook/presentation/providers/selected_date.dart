import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../../core/utils/dates.dart';
import '../../../auth/presentation/providers/auth.dart';

part 'selected_date.g.dart';

/// Date the user is looking at. It starts at the server "today" of the current session and is
/// shared by every page, so the dashboard, the logbook and the planning form agree.
@Riverpod(keepAlive: true)
class SelectedDate extends _$SelectedDate {
  @override
  DateTime build() {
    final today = ref.watch(authProvider.select((session) => session.value?.today));
    return today ?? dateOnly(DateTime.utc(1970));
  }

  void select(DateTime date) => state = dateOnly(date);
}
