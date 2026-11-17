import 'dart:async';

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
import '../providers/auth.dart';
import '../widgets/auth_brand_panel.dart';
import 'access_code_page.dart';

/// Login screen (M1-01a): a dark brand panel and the form. On mobile they stack. An error never
/// says whether the user or the password failed.
///
/// When the server limits the attempts (429, M1-T7) the form shows a fixed message with a countdown of the
/// wait the server communicated, disables the submit button, and enables it again when the wait ends. If
/// the server still holds the restriction, its new 429 starts a new countdown. The screen never shows how
/// many attempts are left nor whether the user exists.
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key, this.startupError, this.clock});

  /// Error found while recovering the session at startup (e.g. access disabled).
  final ApiError? startupError;

  /// Clock used to measure the wait (tests inject one; defaults to the device clock).
  final DateTime Function()? clock;

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _user = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _notice;
  Wait? _wait;
  int _remaining = 0;
  Timer? _ticker;

  DateTime _now() => (widget.clock ?? DateTime.now)();

  @override
  void dispose() {
    _ticker?.cancel();
    _user.dispose();
    _password.dispose();
    super.dispose();
  }

  /// Starts (or restarts) the countdown with the wait the server communicated.
  void _startWait(int seconds) {
    _ticker?.cancel();
    _wait = Wait.from(_now(), seconds);
    _remaining = seconds;
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
  }

  void _tick() {
    final wait = _wait;
    if (!mounted || wait == null) return;
    final remaining = wait.remainingSeconds(_now());
    setState(() {
      _remaining = remaining;
      if (remaining == 0) {
        _ticker?.cancel();
        _wait = null;
        _error = null;
      }
    });
  }

  Future<void> _submit() async {
    if (_busy || _wait != null) return;
    if (_user.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = 'Escribe tu usuario y tu contraseña.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authProvider.notifier).login(user: _user.text.trim(), password: _password.text);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = errorMessage(error);
        _password.clear();
        final seconds = error.retryAfterSeconds;
        if (error.isTooManyRequests && seconds != null) {
          _startWait(seconds);
        }
      });
    }
  }

  /// Opens the first access or recovery screen. When the person completes it, they come back here with a notice and sign in as usual:
  /// those screens never create a session.
  Future<void> _openAccessCode(AccessCodePurpose purpose) async {
    final done = await Navigator.of(context).push<AccessCodePurpose>(
      MaterialPageRoute(builder: (_) => AccessCodePage(purpose: purpose, clock: widget.clock)),
    );
    if (!mounted || done == null) return;
    setState(() {
      _error = null;
      _notice = done == AccessCodePurpose.recovery
          ? 'Tu contraseña cambió y se cerraron tus sesiones anteriores. Ya puedes iniciar sesión.'
          : 'Tu contraseña quedó establecida. Ya puedes iniciar sesión.';
    });
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final message = _error ?? (widget.startupError != null ? errorMessage(widget.startupError!) : null);
    final waiting = _wait != null;
    final visibleMessage = waiting ? 'Demasiados intentos. Vuelve a intentarlo en ${formatWait(_remaining)}.' : message;
    final brand = AuthBrandPanel(mobile: mobile);
    final form = _FormPanel(
      mobile: mobile,
      user: _user,
      password: _password,
      message: visibleMessage,
      // The screen reader announces the message once; the changing countdown is not read every second.
      announcedMessage: waiting ? message : visibleMessage,
      notice: _notice,
      busy: _busy,
      waiting: waiting,
      onSubmit: _submit,
      onFirstAccess: () => _openAccessCode(AccessCodePurpose.firstAccess),
      onRecovery: () => _openAccessCode(AccessCodePurpose.recovery),
    );
    return Scaffold(
      backgroundColor: AppColors.loginBackground,
      body: mobile
          ? SingleChildScrollView(child: Column(children: [brand, form]))
          : Row(children: [Expanded(child: brand), Expanded(child: form)]),
    );
  }
}

class _FormPanel extends StatelessWidget {
  const _FormPanel({
    required this.mobile,
    required this.user,
    required this.password,
    required this.message,
    required this.announcedMessage,
    required this.notice,
    required this.busy,
    required this.waiting,
    required this.onSubmit,
    required this.onFirstAccess,
    required this.onRecovery,
  });

  final bool mobile;
  final TextEditingController user;
  final TextEditingController password;
  final String? message;
  final String? announcedMessage;
  final String? notice;
  final bool busy;
  final bool waiting;
  final VoidCallback onSubmit;
  final VoidCallback onFirstAccess;
  final VoidCallback onRecovery;

  @override
  Widget build(BuildContext context) {
    final card = ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 390),
      child: AutofillGroup(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Eyebrow('Bienvenido de nuevo', bottom: 0),
            Padding(
              padding: const EdgeInsets.only(top: 15, bottom: 10),
              child: Text('Inicia sesión', style: context.heading(28)),
            ),
            const Padding(
              padding: EdgeInsets.only(bottom: 32),
              child: Text(
                'Accede a tu espacio de trabajo y continúa donde lo dejaste.',
                style: TextStyle(fontSize: 13, height: 1.8, color: Color(0xFF8290A3)),
              ),
            ),
            LabeledField(
              fieldKey: const Key('login-id'),
              label: 'Usuario',
              hint: 'Ingresa tu usuario',
              controller: user,
              autofillHints: const [AutofillHints.username],
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 19),
            LabeledField(
              fieldKey: const Key('login-password'),
              label: 'Contraseña',
              hint: 'Ingresa tu contraseña',
              controller: password,
              obscure: true,
              autofillHints: const [AutofillHints.password],
              onSubmitted: (_) => onSubmit(),
            ),
            if (message != null) ...[
              const SizedBox(height: 16),
              if (waiting)
                // The countdown is a plain text node (a screen reader finds the remaining time when it reads the form) and a
                // separate live region announces the fixed message ONCE: a live region whose label changed every second would be
                // read every second.
                Stack(
                  children: [
                    Semantics(
                      liveRegion: true,
                      label: announcedMessage,
                      excludeSemantics: true,
                      child: const SizedBox(width: 1, height: 1),
                    ),
                    Text(
                      message!,
                      key: const Key('login-error'),
                      style: const TextStyle(fontSize: 12, color: AppColors.error),
                    ),
                  ],
                )
              else
                Semantics(
                  liveRegion: true,
                  child: Text(
                    message!,
                    key: const Key('login-error'),
                    style: const TextStyle(fontSize: 12, color: AppColors.error),
                  ),
                ),
            ],
            if (notice != null) ...[
              const SizedBox(height: 16),
              Semantics(
                liveRegion: true,
                child: Text(notice!, key: const Key('login-notice'), style: const TextStyle(fontSize: 12, color: AppColors.teal)),
              ),
            ],
            const SizedBox(height: 22),
            PrimaryButton(
              key: const Key('login-submit'),
              label: 'Ingresar a SMARTWORK',
              trailingIcon: Icons.arrow_forward,
              loading: busy,
              expand: true,
              // Disabled while the server's wait lasts (no request is sent); enabled again when it ends.
              onPressed: waiting ? null : onSubmit,
            ),
            const SizedBox(height: 14),
            // Both screens redeem a code that an operator issued: there is no way to request one from here.
            TextButton(key: const Key('login-first-access'), onPressed: busy ? null : onFirstAccess, child: const Text('Tengo un código de primer acceso')),
            TextButton(key: const Key('login-recovery'), onPressed: busy ? null : onRecovery, child: const Text('Recuperar mi acceso con un código')),
          ],
        ),
      ),
    );
    return Container(
      color: AppColors.loginBackground,
      padding: mobile ? const EdgeInsets.fromLTRB(24, 40, 24, 40) : const EdgeInsets.all(40),
      alignment: mobile ? Alignment.topCenter : Alignment.center,
      child: card,
    );
  }
}
