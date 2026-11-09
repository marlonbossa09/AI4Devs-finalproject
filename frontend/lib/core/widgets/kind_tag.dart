import 'package:flutter/material.dart';

/// A small uppercase tag that says which kind of record a block holds (planning, execution, daily
/// summary...). It tells blocks apart without relying on color alone: it always carries its name.
class KindTag extends StatelessWidget {
  const KindTag(this.text, {super.key, required this.icon, required this.color, required this.background});

  final String text;
  final IconData icon;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(7)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 5),
          Text(
            text.toUpperCase(),
            style: TextStyle(fontSize: 9.5, letterSpacing: 1.1, fontWeight: FontWeight.w800, color: color),
          ),
        ],
      ),
    );
  }
}
