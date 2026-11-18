import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../auth/presentation/providers/auth.dart';

part 'supervision_navigation.g.dart';

/// The activity whose history is open in the supervision area (M4-04). It is cleared with every new session, like the
/// page. Only the id is kept: what the page shows is whatever the server answers for it, never what the list knew.
class SupervisionActivityTargetState {
  const SupervisionActivityTargetState({required this.id});

  final String id;
}

/// The period the supervisor chose and the one last asked for, kept in memory so that coming back from an activity
/// history shows the same view. Cleared with every new session; never written to any storage.
class SupervisionSelectionState {
  const SupervisionSelectionState({this.from, this.to, this.query});

  final DateTime? from;
  final DateTime? to;

  /// The period the view is showing; null until the supervisor asks.
  final ({DateTime from, DateTime to})? query;
}

@Riverpod(keepAlive: true)
class SupervisionSelection extends _$SupervisionSelection {
  @override
  SupervisionSelectionState build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return const SupervisionSelectionState();
  }

  /// Changing a date takes the view away until the supervisor asks again.
  void setFrom(DateTime from) => state = SupervisionSelectionState(from: from, to: state.to);
  void setTo(DateTime to) => state = SupervisionSelectionState(from: state.from, to: to);
  void ask(DateTime from, DateTime to) => state = SupervisionSelectionState(from: from, to: to, query: (from: from, to: to));
  void clearQuery() => state = SupervisionSelectionState(from: state.from, to: state.to);
}

@Riverpod(keepAlive: true)
class SupervisionActivityTarget extends _$SupervisionActivityTarget {
  @override
  SupervisionActivityTargetState? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  void select(String id) => state = SupervisionActivityTargetState(id: id);
}
