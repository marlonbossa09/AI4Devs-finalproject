import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';

/// A small uppercase tag that says which kind of record a block holds (planning, execution, daily
/// summary, calculated, recorded, generated...). It tells blocks apart without relying on color alone: it always
/// carries its name and an icon.
class KindTag extends StatelessWidget {
  const KindTag(this.text, {super.key, required this.icon, required this.color, required this.background});

  final String text;
  final IconData icon;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm, vertical: AppSpace.xs),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(AppRadius.control - 1)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: AppSpace.xs + 1),
          Flexible(
            child: Text(
              text.toUpperCase(),
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: AppType.caption, letterSpacing: 0.7, fontWeight: FontWeight.w800, color: color),
            ),
          ),
        ],
      ),
    );
  }
}
