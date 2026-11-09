import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../../auth/presentation/providers/auth.dart';

part 'unsaved_changes.g.dart';

/// Knows whether some editor on screen holds text that was typed and not saved.
///
/// The editor registers a check and the guard asks it when the user tries to leave, so there is no
/// copy of "dirty" to keep in sync: the answer always comes from the editor itself.
class UnsavedGuard {
  bool Function()? _check;

  void register(bool Function() check) => _check = check;

  /// Only the editor that registered a check can remove it (a newer one is not removed by an older
  /// one being disposed).
  void unregister(bool Function() check) {
    if (_check == check) _check = null; // the same method of the same editor
  }

  bool get hasUnsaved => _check?.call() ?? false;
}

@Riverpod(keepAlive: true)
UnsavedGuard unsavedGuard(Ref ref) => UnsavedGuard();

/// Something the user asked for (change page, change date, sign out) that waits for their decision
/// because it would lose unsaved text.
@immutable
class PendingLeave {
  const PendingLeave(this.proceed);

  final VoidCallback proceed;
}

/// Every way of leaving the screen goes through [request]: it runs the action at once when nothing
/// would be lost, and otherwise holds it until the user chooses to discard the text or keep editing.
@Riverpod(keepAlive: true)
class LeaveRequest extends _$LeaveRequest {
  @override
  PendingLeave? build() {
    ref.watch(authProvider.select((session) => session.value?.user.id)); // a new session starts clean
    return null;
  }

  void request(VoidCallback proceed) {
    if (!ref.read(unsavedGuardProvider).hasUnsaved) {
      proceed();
      return;
    }
    state = PendingLeave(proceed);
  }

  /// The user chose to lose the unsaved text: the held action goes ahead.
  void discard() {
    final pending = state;
    state = null;
    pending?.proceed();
  }

  /// The user chose to keep editing: the held action is dropped and nothing changes.
  void keepEditing() => state = null;
}
