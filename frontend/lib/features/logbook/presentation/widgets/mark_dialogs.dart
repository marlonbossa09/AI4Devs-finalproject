import 'package:flutter/material.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../domain/rules/mark_rules.dart';
import 'action_dialog_frame.dart';

/// Asks for the mandatory reason of marking an activity as registered by mistake (M3-05, RN-59) and
/// sends it. Resolves to true when the activity was marked and to false when the user gave up.
///
/// - [onSubmit] performs the request and throws `ApiError` when the server rejects it; the dialog shows
///   the message and stays open, so the reason can be corrected or the user can give up.
/// - While the request runs the dialog cannot be closed and the buttons do nothing.
Future<bool> showMarkErrorDialog(
  BuildContext context, {
  required String activityTitle,
  required Future<void> Function(String reason) onSubmit,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => _MarkErrorDialog(activityTitle: activityTitle, onSubmit: onSubmit),
  );
  return result ?? false;
}

/// Asks for confirmation before reverting the error mark of an activity (M3-06). No reason is asked: no
/// rule requires one. Resolves to true when the mark was reverted.
Future<bool> showRevertMarkDialog(
  BuildContext context, {
  required String activityTitle,
  required Future<void> Function() onSubmit,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => _RevertMarkDialog(activityTitle: activityTitle, onSubmit: onSubmit),
  );
  return result ?? false;
}

class _MarkErrorDialog extends StatefulWidget {
  const _MarkErrorDialog({required this.activityTitle, required this.onSubmit});

  final String activityTitle;
  final Future<void> Function(String reason) onSubmit;

  @override
  State<_MarkErrorDialog> createState() => _MarkErrorDialogState();
}

class _MarkErrorDialogState extends State<_MarkErrorDialog> {
  final _reason = TextEditingController();
  bool _saving = false;
  String? _fieldError;
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_saving) return; // a second tap while the request runs does nothing
    final problem = validateMarkReason(_reason.text);
    if (problem != null) {
      setState(() {
        _fieldError = problem;
        _error = null;
      });
      return;
    }
    setState(() {
      _saving = true;
      _fieldError = null;
      _error = null;
    });
    try {
      await widget.onSubmit(_reason.text.trim());
      if (mounted) Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      if (error.isNotSignedIn) {
        Navigator.of(context).pop(false); // the session ended: the app goes back to the login
        return;
      }
      setState(() {
        _saving = false;
        _error = errorMessage(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 480;
    return ActionDialogFrame(
      saving: _saving,
      icon: Icons.report_gmailerrorred_outlined,
      title: '¿Marcar como registrada por error?',
      titleKey: const Key('mark-title'),
      intro:
          '«${widget.activityTitle}» saldrá de tus vistas y recuentos, y ya no admitirá avances. No se borra nada: '
          'su historial se conserva y podrás revertir la marca. Queda constancia de la marca y de tu motivo.',
      field: LabeledField(
        fieldKey: const Key('mark-reason'),
        label: 'Motivo *',
        hint: '¿Por qué se registró por error?',
        controller: _reason,
        enabled: !_saving,
        minLines: 3,
        maxLines: 5,
        errorText: _fieldError,
      ),
      error: _error,
      errorKey: const Key('mark-error'),
      cancel: SecondaryButton(
        key: const Key('mark-cancel'),
        label: 'Cancelar',
        onPressed: _saving ? null : () => Navigator.of(context).pop(false),
      ),
      submit: PrimaryButton(
        key: const Key('mark-submit'),
        label: 'Marcar como registrada por error',
        icon: Icons.report_gmailerrorred_outlined,
        loading: _saving,
        expand: narrow,
        onPressed: _submit,
      ),
    );
  }
}

class _RevertMarkDialog extends StatefulWidget {
  const _RevertMarkDialog({required this.activityTitle, required this.onSubmit});

  final String activityTitle;
  final Future<void> Function() onSubmit;

  @override
  State<_RevertMarkDialog> createState() => _RevertMarkDialogState();
}

class _RevertMarkDialogState extends State<_RevertMarkDialog> {
  bool _saving = false;
  String? _error;

  Future<void> _submit() async {
    if (_saving) return; // a second tap while the request runs does nothing
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.onSubmit();
      if (mounted) Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      if (error.isNotSignedIn) {
        Navigator.of(context).pop(false);
        return;
      }
      setState(() {
        _saving = false;
        _error = errorMessage(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 480;
    return ActionDialogFrame(
      saving: _saving,
      icon: Icons.undo,
      title: '¿Revertir la marca de error?',
      titleKey: const Key('revert-title'),
      intro:
          '«${widget.activityTitle}» volverá a tus vistas y recuentos y podrá recibir avances de nuevo. '
          'Queda constancia de la reversión.',
      error: _error,
      errorKey: const Key('revert-error'),
      cancel: SecondaryButton(
        key: const Key('revert-cancel'),
        label: 'Cancelar',
        onPressed: _saving ? null : () => Navigator.of(context).pop(false),
      ),
      submit: PrimaryButton(
        key: const Key('revert-submit'),
        label: 'Revertir marca',
        icon: Icons.undo,
        loading: _saving,
        expand: narrow,
        onPressed: _submit,
      ),
    );
  }
}
