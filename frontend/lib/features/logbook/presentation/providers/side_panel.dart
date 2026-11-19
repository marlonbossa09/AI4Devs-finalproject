import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/providers/auth.dart';
import 'unsaved_changes.dart';

/// What the right-hand side panel shows: a header, a body that scrolls on its own and an optional strip of actions.
///
/// This is only the INFRASTRUCTURE (UX-T2): no feature opens a panel yet and the panel talks to no endpoint. A feature that uses it
/// builds its own form inside [bodyBuilder] and registers its unsaved text with the same `UnsavedGuard` as every other editor.
@immutable
class SidePanelRequest {
  const SidePanelRequest({
    required this.title,
    required this.bodyBuilder,
    this.subtitle,
    this.icon = Icons.add,
    this.actionsBuilder,
    this.isBusy,
    this.hasUnsaved,
  });

  final String title;
  final String? subtitle;
  final IconData icon;
  final WidgetBuilder bodyBuilder;

  /// Strip pinned under the body (for example Cancel and Save). Optional.
  final WidgetBuilder? actionsBuilder;

  /// True while the panel is sending something. A busy panel cannot be closed or replaced: closing it would leave the person without
  /// knowing whether it was saved.
  final bool Function()? isBusy;

  /// Whether the panel holds text that was typed and not saved. Closing or replacing it asks first only when this is true.
  final bool Function()? hasUnsaved;
}

/// The panel that is open (null = none). It is closed by a new session, like the page.
///
/// Every way of closing it that the user starts (the X, Escape, tapping outside, changing page, signing out) goes through the same
/// `LeaveRequest` as the rest of the app, so text that was typed and not saved is never lost without asking.
class SidePanelNotifier extends Notifier<SidePanelRequest?> {
  @override
  SidePanelRequest? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id));
    return null;
  }

  /// Opens [request]. If another panel is open with unsaved text, the user is asked first.
  void open(SidePanelRequest request) {
    if (state?.isBusy?.call() ?? false) return;
    if (state == null) {
      state = request;
      return;
    }
    ref.read(leaveRequestProvider.notifier).requestWhen(() => state?.hasUnsaved?.call() ?? false, () => state = request);
  }

  /// The user asked to close the panel (X, Escape, tap outside, Cancel): it waits for their decision if it would lose text.
  void requestClose() {
    if (state == null || (state!.isBusy?.call() ?? false)) return;
    ref.read(leaveRequestProvider.notifier).requestWhen(() => state?.hasUnsaved?.call() ?? false, () => state = null);
  }

  /// Closes the panel at once, with no question. Only for what has already been decided (the user confirmed leaving, a save succeeded).
  void closeNow() => state = null;
}

final sidePanelProvider = NotifierProvider<SidePanelNotifier, SidePanelRequest?>(SidePanelNotifier.new);
