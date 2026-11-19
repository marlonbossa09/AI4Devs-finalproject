import 'package:flutter/material.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../domain/rules/closing_rules.dart';
import 'action_dialog_frame.dart';

/// Asks for the mandatory reason of a reopening (M3-02, RN-50) and sends it. Resolves to true when the
/// logbook was reopened and to false when the user gave up.
///
/// - [onSubmit] performs the request and throws `ApiError` when the server rejects it; the dialog shows
///   the message next to the field and stays open so the reason can be corrected.
/// - While the request runs the dialog cannot be closed and the buttons do nothing.
Future<bool> showReopenDialog(BuildContext context, {required Future<void> Function(String reason) onSubmit}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => _ReopenDialog(onSubmit: onSubmit),
  );
  return result ?? false;
}

class _ReopenDialog extends StatefulWidget {
  const _ReopenDialog({required this.onSubmit});

  final Future<void> Function(String reason) onSubmit;

  @override
  State<_ReopenDialog> createState() => _ReopenDialogState();
}

class _ReopenDialogState extends State<_ReopenDialog> {
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
    final problem = validateReopenReason(_reason.text);
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
    final cancel = SecondaryButton(
      key: const Key('reopen-cancel'),
      label: 'Cancelar',
      onPressed: _saving ? null : () => Navigator.of(context).pop(false),
    );
    final submit = PrimaryButton(
      key: const Key('reopen-submit'),
      label: 'Reabrir jornada',
      icon: Icons.lock_open_outlined,
      loading: _saving,
      expand: narrow,
      onPressed: _submit,
    );
    return ActionDialogFrame(
      saving: _saving,
      icon: Icons.lock_open_outlined,
      title: '¿Reabrir la jornada?',
      titleKey: const Key('reopen-title'),
      intro:
          'Podrás corregir su contenido. Queda constancia de la reapertura y de tu motivo, y la jornada '
          'habrá que cerrarla de nuevo.',
      field: LabeledField(
        fieldKey: const Key('reopen-reason'),
        label: 'Motivo de la reapertura *',
        hint: '¿Qué necesitas corregir?',
        controller: _reason,
        enabled: !_saving,
        minLines: 3,
        maxLines: 5,
        errorText: _fieldError,
      ),
      error: _error,
      errorKey: const Key('reopen-error'),
      cancel: cancel,
      submit: submit,
    );
  }
}
