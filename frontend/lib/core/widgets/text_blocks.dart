import 'package:flutter/material.dart';

import '../layout/screen_size.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/app_tokens.dart';

/// Small uppercase label above a title (`.eyebrow`).
class Eyebrow extends StatelessWidget {
  const Eyebrow(this.text, {super.key, this.color = AppColors.teal, this.bottom = AppSpace.xs});

  final String text;
  final Color color;
  final double bottom;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: bottom),
      child: Text(
        text.toUpperCase(),
        style: TextStyle(fontSize: AppType.caption, letterSpacing: 1.2, fontWeight: FontWeight.w800, color: color),
      ),
    );
  }
}

/// Eyebrow, title (20 px), subtitle and an optional main action (`.header-line`). Compact: about 70 px before the content.
class PageHeader extends StatelessWidget {
  const PageHeader({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
    this.titleTrailing,
    this.action,
  });

  final String eyebrow;
  final String title;
  final String subtitle;
  final Widget? titleTrailing;
  final Widget? action;

  /// Content width from which the action fits beside the title.
  static const double _sideBySideMinWidth = 760;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final heading = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Flexible(child: Text(title, style: context.heading(AppType.pageTitle, height: 1.3))),
            if (titleTrailing != null) ...[const SizedBox(width: 8), titleTrailing!],
          ],
        ),
        const SizedBox(height: AppSpace.xs),
        Text(subtitle, style: const TextStyle(fontSize: AppType.body, color: AppColors.muted)),
      ],
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.xl),
      // The action goes beside the title only when there is room for both; with less than
      // [_sideBySideMinWidth] (a tablet with the sidebar open, or a phone) it goes under it.
      child: LayoutBuilder(
        builder: (context, constraints) {
          final stacked = mobile || constraints.maxWidth < _sideBySideMinWidth;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Eyebrow(eyebrow),
              if (action == null)
                heading
              else if (stacked)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [heading, const SizedBox(height: AppSpace.md), action!],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  // The action takes the room it needs but never more than 3/5 of the line: a row of buttons wraps instead of overflowing.
                  children: [
                    Expanded(flex: 2, child: heading),
                    const SizedBox(width: AppSpace.lg),
                    Flexible(flex: 3, child: Align(alignment: Alignment.centerRight, child: action!)),
                  ],
                ),
            ],
          );
        },
      ),
    );
  }
}

/// Centered message for a list with nothing to show (`.empty`).
class EmptyState extends StatelessWidget {
  const EmptyState(this.message, {super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.xxl, horizontal: AppSpace.sm),
      child: Center(
        child: Text(
          message,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: AppType.body, color: AppColors.textSecondary),
        ),
      ),
    );
  }
}

/// Informative message with a soft blue background (`.notice`). Information is blue; teal stays for interaction.
class Notice extends StatelessWidget {
  const Notice({super.key, required this.title, required this.text, this.icon});

  final String title;
  final String text;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.md + 2),
      decoration: BoxDecoration(
        color: AppColors.infoBackground,
        border: Border.all(color: AppColors.infoBorder),
        borderRadius: BorderRadius.circular(AppRadius.control + 2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (icon != null) ...[Icon(icon, size: 16, color: AppColors.infoText), const SizedBox(width: AppSpace.sm - 1)],
              Flexible(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.infoText),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.xs),
          Text(text, style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.infoText)),
        ],
      ),
    );
  }
}

/// Error message with a retry action, for a panel that could not load.
class ErrorBox extends StatelessWidget {
  const ErrorBox({super.key, required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Column(
        children: [
          Text(
            message,
            key: const Key('load-error'),
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: AppType.body, color: AppColors.error),
          ),
          const SizedBox(height: AppSpace.sm),
          TextButton(
            onPressed: onRetry,
            style: TextButton.styleFrom(foregroundColor: AppColors.primary, minimumSize: const Size(AppSize.minTouch, AppSize.minTouch)),
            child: const Text('Reintentar'),
          ),
        ],
      ),
    );
  }
}
