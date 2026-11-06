import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/brand.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../providers/auth.dart';

/// Login screen (M1-01a): a dark brand panel and the form. On mobile they stack. An error never
/// says whether the user or the password failed.
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key, this.startupError});

  /// Error found while recovering the session at startup (e.g. access disabled).
  final ApiError? startupError;

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _user = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _user.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy) return;
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
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final message = _error ?? (widget.startupError != null ? errorMessage(widget.startupError!) : null);
    final brand = _BrandPanel(mobile: mobile);
    final form = _FormPanel(
      mobile: mobile,
      user: _user,
      password: _password,
      message: message,
      busy: _busy,
      onSubmit: _submit,
    );
    return Scaffold(
      backgroundColor: AppColors.loginBackground,
      body: mobile
          ? SingleChildScrollView(child: Column(children: [brand, form]))
          : Row(children: [Expanded(child: brand), Expanded(child: form)]),
    );
  }
}

class _BrandPanel extends StatelessWidget {
  const _BrandPanel({required this.mobile});

  final bool mobile;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final headline = (width * 0.032).clamp(32.0, 50.0);
    final content = Padding(
      padding: mobile
          ? const EdgeInsets.fromLTRB(25, 30, 25, 30)
          : EdgeInsets.symmetric(horizontal: width * 0.09, vertical: 75),
      child: Column(
        mainAxisAlignment: mobile ? MainAxisAlignment.start : MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: mobile ? MainAxisSize.min : MainAxisSize.max,
        children: [
          Row(
            children: [
              const LogoMark(),
              const SizedBox(width: 12),
              Text('SMARTWORK', style: context.heading(20, color: AppColors.white)),
            ],
          ),
          if (mobile) const SizedBox(height: 40),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Eyebrow('Tu trabajo, con claridad'),
              Text.rich(
                TextSpan(
                  style: context.heading(mobile ? 29 : headline, color: AppColors.white, height: 1.2, letterSpacing: -1),
                  children: const [
                    TextSpan(text: 'Organiza tu día.\n'),
                    TextSpan(text: 'Haz visible tu progreso.', style: TextStyle(color: AppColors.accent)),
                  ],
                ),
              ),
              if (!mobile) ...[
                const SizedBox(height: 22),
                ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: 420),
                  child: Text(
                    'Un espacio simple para planificar actividades, registrar avances y mantener un historial claro de tu trabajo.',
                    style: TextStyle(fontSize: 15, height: 1.85, color: Color(0xFFAABBD0)),
                  ),
                ),
              ],
            ],
          ),
          if (!mobile)
            const Text(
              'SMARTWORK · 2026',
              style: TextStyle(fontSize: 11, color: Color(0xFF7790A9)),
            ),
        ],
      ),
    );

    return Container(
      constraints: mobile ? const BoxConstraints(minHeight: 250) : null,
      clipBehavior: Clip.hardEdge,
      decoration: const BoxDecoration(color: AppColors.navyLogin),
      child: Stack(
        children: [
          Positioned(
            right: -180,
            bottom: -180,
            child: IgnorePointer(
              child: Container(
                width: 580,
                height: 580,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: const Color(0x2B54DDC5)),
                  boxShadow: const [
                    BoxShadow(color: Color(0x101C897A), spreadRadius: 75),
                    BoxShadow(color: Color(0x0C1C897A), spreadRadius: 150),
                  ],
                ),
              ),
            ),
          ),
          content,
        ],
      ),
    );
  }
}

class _FormPanel extends StatelessWidget {
  const _FormPanel({
    required this.mobile,
    required this.user,
    required this.password,
    required this.message,
    required this.busy,
    required this.onSubmit,
  });

  final bool mobile;
  final TextEditingController user;
  final TextEditingController password;
  final String? message;
  final bool busy;
  final VoidCallback onSubmit;

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
              Semantics(
                liveRegion: true,
                child: Text(
                  message!,
                  key: const Key('login-error'),
                  style: const TextStyle(fontSize: 12, color: AppColors.error),
                ),
              ),
            ],
            const SizedBox(height: 22),
            PrimaryButton(
              key: const Key('login-submit'),
              label: 'Ingresar a SMARTWORK',
              trailingIcon: Icons.arrow_forward,
              loading: busy,
              expand: true,
              onPressed: onSubmit,
            ),
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
