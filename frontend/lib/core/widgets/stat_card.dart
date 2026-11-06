import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'app_card.dart';

/// One indicator of the summary row: label, icon, big number and a note (`.stat`).
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

  /// Smaller paddings and number, for mobile.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: compact
          ? const EdgeInsets.all(15)
          : const EdgeInsets.fromLTRB(21, 21, 21, 19),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  maxLines: compact ? 2 : 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF718198)),
                ),
              ),
              const SizedBox(width: 6),
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: const Color(0xFFEEF5FB),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Icon(icon, size: 17, color: const Color(0xFF4C829D)),
              ),
            ],
          ),
          SizedBox(height: compact ? 12 : 17),
          Text('$value', style: context.heading(compact ? 23 : 29)),
          const SizedBox(height: 6),
          Text(
            caption,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, color: Color(0xFF8491A4)),
          ),
        ],
      ),
    );
  }
}
