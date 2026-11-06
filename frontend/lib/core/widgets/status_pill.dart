import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

enum PillKind { pending, progress, blocked, done }

/// Small rounded label with the colors of an activity status (`.pill`).
class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.kind});

  final String label;
  final PillKind kind;

  (Color, Color) get _colors => switch (kind) {
    PillKind.pending => (AppColors.pendingBackground, AppColors.pendingText),
    PillKind.progress => (AppColors.progressBackground, AppColors.progressText),
    PillKind.blocked => (AppColors.blockedBackground, AppColors.blockedText),
    PillKind.done => (AppColors.doneBackground, AppColors.doneText),
  };

  @override
  Widget build(BuildContext context) {
    final (background, text) = _colors;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(20)),
      child: Text(
        label,
        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: text),
      ),
    );
  }
}
