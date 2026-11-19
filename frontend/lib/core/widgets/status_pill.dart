import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_tokens.dart';

enum PillKind { pending, progress, blocked, done }

/// Small rounded label with the colors of an activity status (`.pill`): amber (pending), blue (in progress), green
/// (done) and red (blocked). A status is never told by color alone: the pill carries its word and an icon.
class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.kind});

  final String label;
  final PillKind kind;

  (Color, Color, IconData) get _look => switch (kind) {
    PillKind.pending => (AppColors.pendingBackground, AppColors.pendingText, Icons.schedule),
    PillKind.progress => (AppColors.progressBackground, AppColors.progressText, Icons.play_arrow_rounded),
    PillKind.blocked => (AppColors.blockedBackground, AppColors.blockedText, Icons.block),
    PillKind.done => (AppColors.doneBackground, AppColors.doneText, Icons.check_circle_outline),
  };

  @override
  Widget build(BuildContext context) {
    final (background, text, icon) = _look;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm + 2, vertical: AppSpace.xs),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(AppRadius.pill)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: text),
          const SizedBox(width: AppSpace.xs),
          Flexible(
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: text),
            ),
          ),
        ],
      ),
    );
  }
}
