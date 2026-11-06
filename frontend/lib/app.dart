import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/errors/api_error.dart';
import 'core/theme/app_colors.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/pages/login_page.dart';
import 'features/auth/presentation/providers/auth.dart';
import 'features/logbook/presentation/pages/home_page.dart';

class SmartworkApp extends StatelessWidget {
  /// [webFonts] loads the design fonts (DM Sans and Manrope) from Google Fonts. Tests turn it
  /// off so they never use the network.
  const SmartworkApp({super.key, this.webFonts = true});

  final bool webFonts;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SMARTWORK',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.build(webFonts: webFonts),
      home: const _AuthGate(),
    );
  }
}

/// Without a session nothing of the logbooks is shown (CA-01).
class _AuthGate extends ConsumerWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    return auth.when(
      loading: () => const Scaffold(
        backgroundColor: AppColors.background,
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (error, _) => LoginPage(startupError: error is ApiError ? error : null),
      data: (session) => session == null ? const LoginPage() : HomePage(session: session),
    );
  }
}
