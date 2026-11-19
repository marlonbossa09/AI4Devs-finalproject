import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/app_tokens.dart';
import 'app_card.dart';

/// One indicator of the summary row (`.stat`), compact: a neutral icon box, the label, the figure and its note in one
/// short block. The icon box is neutral (teal is reserved for interaction); the figure is the count the screen was given,
/// never a percentage or a computed trend.
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.caption,
    required this.icon,
    this.compact = false,
  });

  final String label;
  final int value;
  final String caption;
  final IconData icon;

  /// Smaller paddings and figure, for mobile.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: EdgeInsets.all(compact ? AppSpace.md : AppSpace.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: compact ? 32 : 36,
            height: compact ? 32 : 36,
            decoration: BoxDecoration(
              color: AppColors.recordedBackground,
              borderRadius: BorderRadius.circular(AppRadius.control),
            ),
            child: Icon(icon, size: 18, color: AppColors.textSecondary),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: compact ? 2 : 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 2),
                Text('$value', style: context.heading(compact ? AppType.pageTitle : AppType.metric, height: 1.2)),
                const SizedBox(height: 2),
                Text(
                  caption,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
