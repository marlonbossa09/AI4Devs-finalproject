import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/widgets/confirm_dialog.dart';
import '../providers/unsaved_changes.dart';

/// Shows the confirmation when the user tries to leave with unsaved text (a page change, a date
/// change, signing out, or closing or replacing a side panel), and tells the pending request what they chose. It is ONE question,
/// whatever editor holds the text (the daily summary, a side-panel form...).
///
/// - "Seguir editando" (also Escape or tapping outside) keeps everything as it is.
/// - "Descartar cambios" lets the held action go ahead, and the text is lost.
class UnsavedChangesHost extends ConsumerStatefulWidget {
  const UnsavedChangesHost({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<UnsavedChangesHost> createState() => _UnsavedChangesHostState();
}

class _UnsavedChangesHostState extends ConsumerState<UnsavedChangesHost> {
  bool _asking = false;

  Future<void> _ask() async {
    _asking = true;
    final discard = await showConfirmDialog(
      context,
      title: 'Tienes cambios sin guardar',
      message: 'Hay información escrita que todavía no se ha guardado. Si continúas, se perderá.',
      confirmLabel: 'Descartar cambios',
      cancelLabel: 'Seguir editando',
    );
    _asking = false;
    if (!mounted) return;
    final leave = ref.read(leaveRequestProvider.notifier);
    discard ? leave.discard() : leave.keepEditing();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(leaveRequestProvider, (previous, next) {
      if (next != null && !_asking) {
        _ask();
      } else if (next == null && _asking) {
        // The request ended by itself (the session ended): the question no longer applies
        Navigator.of(context, rootNavigator: true).pop(false);
      }
    });
    return widget.child;
  }
}
