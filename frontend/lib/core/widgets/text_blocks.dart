import 'package:flutter/material.dart';

import '../layout/screen_size.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Small uppercase label above a title (`.eyebrow`).
class Eyebrow extends StatelessWidget {
  const Eyebrow(this.text, {super.key, this.color = AppColors.teal, this.bottom = 8});

  final String text;
  final Color color;
  final double bottom;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: bottom),
      child: Text(
        text.toUpperCase(),
        style: TextStyle(fontSize: 11, letterSpacing: 1.7, fontWeight: FontWeight.w800, color: color),
      ),
    );
  }
}

/// Eyebrow, title, subtitle and an optional main action (`.header-line`).
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
            Flexible(child: Text(title, style: context.heading(mobile ? 23 : 28, height: 1.3))),
            if (titleTrailing != null) ...[const SizedBox(width: 8), titleTrailing!],
          ],
        ),
        const SizedBox(height: 7),
        Text(subtitle, style: const TextStyle(fontSize: 13, color: AppColors.muted)),
      ],
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 29),
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
                  children: [heading, const SizedBox(height: 16), action!],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [Expanded(child: heading), const SizedBox(width: 15), action!],
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
      padding: const EdgeInsets.symmetric(vertical: 35, horizontal: 10),
      child: Center(
        child: Text(
          message,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 13, color: Color(0xFF8292A2)),
        ),
      ),
    );
  }
}

/// Message with a soft teal background (`.notice`).
class Notice extends StatelessWidget {
  const Notice({super.key, required this.title, required this.text, this.icon});

  final String title;
  final String text;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFEBF7F4),
        border: Border.all(color: const Color(0xFFDAEEE9)),
        borderRadius: BorderRadius.circular(11),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (icon != null) ...[Icon(icon, size: 14, color: const Color(0xFF276A67)), const SizedBox(width: 6)],
              Flexible(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF276A67)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Text(text, style: const TextStyle(fontSize: 11, height: 1.65, color: Color(0xFF276A67))),
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
            style: const TextStyle(fontSize: 13, color: AppColors.error),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: onRetry,
            style: TextButton.styleFrom(foregroundColor: const Color(0xFF14998F)),
            child: const Text('Reintentar'),
          ),
        ],
      ),
    );
  }
}
