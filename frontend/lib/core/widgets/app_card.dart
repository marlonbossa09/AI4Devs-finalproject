import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// White panel with a thin border, rounded corners and a soft shadow (`.panel` in the design).
class AppCard extends StatelessWidget {
  const AppCard({super.key, required this.child, this.padding, this.color = AppColors.white});

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: AppColors.border),
        boxShadow: const [BoxShadow(color: Color(0x081A3450), blurRadius: 19, offset: Offset(0, 5))],
      ),
      child: child,
    );
  }
}

/// Title and subtitle of a panel, with an optional widget at the end (`.panel-hd`).
class PanelHeader extends StatelessWidget {
  const PanelHeader({super.key, required this.title, this.subtitle, this.trailing});

  final String title;
  final String? subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: context.heading(15)),
                if (subtitle != null) ...[
                  const SizedBox(height: 6),
                  Text(subtitle!, style: const TextStyle(fontSize: 12, color: Color(0xFF8B97A6))),
                ],
              ],
            ),
          ),
          if (trailing != null) ...[const SizedBox(width: 12), trailing!],
        ],
      ),
    );
  }
}

/// Bottom strip of a panel with a note and an optional action (`.panel-footer`).
class PanelFooter extends StatelessWidget {
  const PanelFooter({super.key, required this.text, this.action});

  final String text;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 15),
      decoration: const BoxDecoration(
        color: AppColors.panelFooter,
        border: Border(top: BorderSide(color: Color(0xFFEDF0F5))),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: 12,
        runSpacing: 4,
        children: [
          Text(text, style: const TextStyle(fontSize: 11, color: Color(0xFF8190A5))),
          if (action != null) action!,
        ],
      ),
    );
  }
}
