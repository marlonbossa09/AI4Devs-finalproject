import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/brand.dart';
import '../../../../core/widgets/text_blocks.dart';

/// Dark brand panel shared by the login, first access and recovery screens. On mobile it stacks above the form.
class AuthBrandPanel extends StatelessWidget {
  const AuthBrandPanel({super.key, required this.mobile});

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
