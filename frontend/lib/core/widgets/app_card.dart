import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/app_tokens.dart';

/// White card with a thin border, 12 px corners and a soft shadow (`.panel` in the design).
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
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
        boxShadow: AppShadow.card,
      ),
      child: child,
    );
  }
}

/// Title and subtitle of a panel, with an optional widget at the end (`.panel-hd`).
class PanelHeader extends StatelessWidget {
  const PanelHeader({super.key, required this.title, this.subtitle, this.trailing, this.bottom = AppSpace.lg});

  final String title;
  final String? subtitle;
  final Widget? trailing;

  /// Space under the header (16 by default; a panel that needs more air can pass 20 or 24).
  final double bottom;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: bottom),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: context.heading(AppType.cardTitle)),
                if (subtitle != null) ...[
                  const SizedBox(height: AppSpace.xs),
                  Text(subtitle!, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
                ],
              ],
            ),
          ),
          if (trailing != null) ...[const SizedBox(width: AppSpace.md), trailing!],
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
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.xxl, vertical: AppSpace.md),
      decoration: const BoxDecoration(
        color: AppColors.panelFooter,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: AppSpace.md,
        runSpacing: AppSpace.xs,
        children: [
          Text(text, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
          if (action != null) action!,
        ],
      ),
    );
  }
}
