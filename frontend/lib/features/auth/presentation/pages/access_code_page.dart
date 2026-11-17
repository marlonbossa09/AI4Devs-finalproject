import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/wait.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/repository/access_code_repository.dart';
import '../providers/access_code_repository.dart';
import '../widgets/auth_brand_panel.dart';

/// Minimum length of a password. The server is the authority (`CONTRASENA_NO_VALIDA`); this only saves a round trip.
const int minPasswordLength = 10;

/// First access (M1-03b) and recovery (M1-09b): the person types the one-time code an operator gave them and chooses a new password.
///
/// - Nothing is kept: the code and the passwords live only in the text fields of this screen, are cleared after a failure and disappear
///   with the screen. They are never stored, logged or put in navigation parameters.
/// - It never signs the person in. On success it returns to the login (popping with the [purpose]) so there is one single way to create
///   a session.
/// - Every code that does not work gets the same message; a weak password gets its own message whether the code is valid or not.
/// - A 429 shows a countdown of the time the server communicated and disables the button until it ends.
/// - There is no way to ask for a code here: recovery is administrative and out of band (the operator issues it).
class AccessCodePage extends ConsumerStatefulWidget {
  const AccessCodePage({super.key, required this.purpose, this.clock});

  final AccessCodePurpose purpose;

  /// Clock used to measure the wait (tests inject one; defaults to the device clock).
  final DateTime Function()? clock;

  @override
  ConsumerState<AccessCodePage> createState() => _AccessCodePageState();
}

class _AccessCodePageState extends ConsumerState<AccessCodePage> {
  final _identifier = TextEditingController();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirmation = TextEditingController();
  bool _busy = false;
  bool _showPasswords = false;
  String? _message;
  String? _identifierError;
  String? _codeError;
  String? _passwordError;
  String? _confirmationError;
  late final WaitTicker _wait = WaitTicker(now: _now, onChange: _onWaitChange);

  bool get _isRecovery => widget.purpose == AccessCodePurpose.recovery;

  DateTime _now() => (widget.clock ?? DateTime.now)();

  void _onWaitChange() {
    if (!mounted) return;
    setState(() {
      if (!_wait.active) _message = null;
    });
  }

  @override
  void dispose() {
    _wait.cancel();
    _identifier.dispose();
    _code.dispose();
    _password.dispose();
    _confirmation.dispose();
    super.dispose();
  }

  bool _validate() {
    final identifier = _identifier.text.trim().isEmpty ? 'Escribe tu usuario.' : null;
    final code = _code.text.trim().isEmpty ? 'Escribe el código que te entregaron.' : null;
    final password = _password.text.length < minPasswordLength ? 'La contraseña debe tener al menos $minPasswordLength caracteres.' : null;
    final confirmation = password == null && _confirmation.text != _password.text ? 'Las contraseñas no coinciden.' : null;
    setState(() {
      _identifierError = identifier;
      _codeError = code;
      _passwordError = password;
      _confirmationError = confirmation;
      _message = null;
    });
    return identifier == null && code == null && password == null && confirmation == null;
  }

  Future<void> _submit() async {
    if (_busy || _wait.active) return; // no duplicate requests, no request while the server asks to wait
    if (!_validate()) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(accessCodeRepositoryProvider)
          .redeem(widget.purpose, identifier: _identifier.text.trim(), code: _code.text.trim(), newPassword: _password.text);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _password.clear();
        _confirmation.clear();
        _message = errorMessage(error);
        final seconds = error.retryAfterSeconds;
        if (error.isTooManyRequests && seconds != null) _wait.start(seconds);
      });
      return;
    }
    if (!mounted) return;
    // Nothing is kept: the fields are emptied before leaving. The person signs in afterwards, with the login.
    _code.clear();
    _password.clear();
    _confirmation.clear();
    Navigator.of(context).pop(widget.purpose);
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final waiting = _wait.active;
    final visible = waiting ? 'Demasiados intentos. Vuelve a intentarlo en ${formatWait(_wait.remaining)}.' : _message;
    final form = _Form(
      recovery: _isRecovery,
      mobile: mobile,
      identifier: _identifier,
      code: _code,
      password: _password,
      confirmation: _confirmation,
      showPasswords: _showPasswords,
      onToggle: () => setState(() => _showPasswords = !_showPasswords),
      identifierError: _identifierError,
      codeError: _codeError,
      passwordError: _passwordError,
      confirmationError: _confirmationError,
      message: visible,
      announcedMessage: waiting ? _message : visible,
      busy: _busy,
      waiting: waiting,
      onSubmit: _submit,
      onBack: () => Navigator.of(context).pop(),
    );
    final brand = AuthBrandPanel(mobile: mobile);
    return Scaffold(
      backgroundColor: AppColors.loginBackground,
      body: mobile
          ? SingleChildScrollView(child: Column(children: [brand, form]))
          : Row(children: [Expanded(child: brand), Expanded(child: form)]),
    );
  }
}

class _Form extends StatelessWidget {
  const _Form({
    required this.recovery,
    required this.mobile,
    required this.identifier,
    required this.code,
    required this.password,
    required this.confirmation,
    required this.showPasswords,
    required this.onToggle,
    required this.identifierError,
    required this.codeError,
    required this.passwordError,
    required this.confirmationError,
    required this.message,
    required this.announcedMessage,
    required this.busy,
    required this.waiting,
    required this.onSubmit,
    required this.onBack,
  });

  final bool recovery;
  final bool mobile;
  final TextEditingController identifier;
  final TextEditingController code;
  final TextEditingController password;
  final TextEditingController confirmation;
  final bool showPasswords;
  final VoidCallback onToggle;
  final String? identifierError;
  final String? codeError;
  final String? passwordError;
  final String? confirmationError;
  final String? message;
  final String? announcedMessage;
  final bool busy;
  final bool waiting;
  final VoidCallback onSubmit;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final toggle = IconButton(
      key: const Key('access-toggle-passwords'),
      tooltip: showPasswords ? 'Ocultar las contraseñas' : 'Mostrar las contraseñas',
      icon: Icon(showPasswords ? Icons.visibility_off_outlined : Icons.visibility_outlined, size: 19),
      onPressed: onToggle,
    );
    final card = ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 390),
      child: AutofillGroup(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Eyebrow(recovery ? 'Recuperar el acceso' : 'Primer acceso', bottom: 0),
            Padding(
              padding: const EdgeInsets.only(top: 15, bottom: 10),
              child: Semantics(
                header: true,
                child: Text(recovery ? 'Elige una contraseña nueva' : 'Establece tu contraseña', style: context.heading(28)),
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 24),
              child: Text(
                recovery
                    ? 'Quien administra el servicio verificó tu identidad y te entregó un código. Al terminar se cerrarán tus sesiones abiertas. '
                          'Si no tienes un código, pídelo a quien administra el servicio: no se envía por correo ni por mensaje.'
                    : 'Escribe el código que te entregó en persona quien administra el servicio y elige tu contraseña. '
                          'Si no lo tienes, pídelo a quien administra el servicio.',
                style: const TextStyle(fontSize: 13, height: 1.7, color: Color(0xFF8290A3)),
              ),
            ),
            LabeledField(
              fieldKey: const Key('access-identifier'),
              label: 'Usuario',
              hint: 'Ingresa tu usuario',
              controller: identifier,
              errorText: identifierError,
              enabled: !busy,
              autofillHints: const [AutofillHints.username],
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 17),
            LabeledField(
              fieldKey: const Key('access-code'),
              label: 'Código',
              hint: 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXXX',
              hintBelow: 'Puedes escribirlo con o sin guiones.',
              controller: code,
              errorText: codeError,
              enabled: !busy,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 17),
            LabeledField(
              fieldKey: const Key('access-password'),
              label: 'Contraseña nueva',
              hint: 'Al menos $minPasswordLength caracteres',
              controller: password,
              errorText: passwordError,
              enabled: !busy,
              obscure: !showPasswords,
              suffix: toggle,
              autofillHints: const [AutofillHints.newPassword],
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 17),
            LabeledField(
              fieldKey: const Key('access-confirmation'),
              label: 'Confirma la contraseña',
              hint: 'Escríbela otra vez',
              controller: confirmation,
              errorText: confirmationError,
              enabled: !busy,
              obscure: !showPasswords,
              autofillHints: const [AutofillHints.newPassword],
              onSubmitted: (_) => onSubmit(),
            ),
            if (message != null) ...[
              const SizedBox(height: 16),
              if (waiting)
                // The countdown is plain text; a separate live region announces the fixed message once (see the login screen).
                Stack(
                  children: [
                    Semantics(
                      liveRegion: true,
                      label: announcedMessage,
                      excludeSemantics: true,
                      child: const SizedBox(width: 1, height: 1),
                    ),
                    Text(message!, key: const Key('access-error'), style: const TextStyle(fontSize: 12, color: AppColors.error)),
                  ],
                )
              else
                Semantics(
                  liveRegion: true,
                  child: Text(message!, key: const Key('access-error'), style: const TextStyle(fontSize: 12, color: AppColors.error)),
                ),
            ],
            const SizedBox(height: 22),
            PrimaryButton(
              key: const Key('access-submit'),
              label: recovery ? 'Cambiar contraseña' : 'Establecer contraseña',
              trailingIcon: Icons.arrow_forward,
              loading: busy,
              expand: true,
              // Disabled while a request is in flight (loading) and while the server's wait lasts.
              onPressed: waiting ? null : onSubmit,
            ),
            const SizedBox(height: 10),
            TextButton(
              key: const Key('access-back'),
              onPressed: busy ? null : onBack,
              child: const Text('Volver al inicio de sesión'),
            ),
          ],
        ),
      ),
    );
    return Container(
      color: AppColors.loginBackground,
      padding: mobile ? const EdgeInsets.fromLTRB(24, 32, 24, 32) : const EdgeInsets.all(40),
      alignment: mobile ? Alignment.topCenter : Alignment.center,
      child: mobile ? card : SingleChildScrollView(child: card),
    );
  }
}
