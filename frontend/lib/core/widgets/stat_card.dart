import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/app_tokens.dart';
import 'app_card.dart';

/// One indicator of the summary row (`.stat`), compact: an icon box, the label, the figure and its note in one short
/// block. The figure is the count the screen was given, never a percentage or a computed trend. A screen that has no
/// figure yet (it is still loading, or it failed) passes a null [value] and the card shows a dash, never a made-up zero.
///
/// The whole card is read as ONE sentence ("Pendientes: 2, estado actual"), not as four separate fragments.
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.caption,
    required this.icon,
    this.compact = false,
    this.showCaption = true,
    this.iconBackground = AppColors.recordedBackground,
    this.iconColor = AppColors.textSecondary,
  });

  final String label;

  /// The count, or null when it is not known (yet).
  final int? value;
  final String caption;
  final IconData icon;

  /// Smaller paddings and figure, for mobile.
  final bool compact;

  /// Whether the note is drawn. A screen that already says it once for the whole row (and where height is scarce) can hide
  /// it; a screen reader still gets it, as the hint of the card.
  final bool showCaption;

  /// Colors of the icon box. Neutral by default; a status can tint it, but its word always travels with it.
  final Color iconBackground;
  final Color iconColor;

  @override
  Widget build(BuildContext context) {
    final figure = value == null ? '–' : '$value';
    return MergeSemantics(
      child: Semantics(
        label: value == null ? '$label: sin datos' : '$label: $value',
        hint: caption,
        excludeSemantics: true,
        child: AppCard(
          padding: EdgeInsets.all(compact ? AppSpace.md : AppSpace.lg),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: compact ? 32 : 36,
                height: compact ? 32 : 36,
                decoration: BoxDecoration(color: iconBackground, borderRadius: BorderRadius.circular(AppRadius.control)),
                child: Icon(icon, size: 18, color: iconColor),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 2),
                    Text(figure, style: context.heading(compact ? AppType.pageTitle : AppType.metric, height: 1.2)),
                    if (showCaption) ...[
                      const SizedBox(height: 2),
                      Text(
                        caption,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
