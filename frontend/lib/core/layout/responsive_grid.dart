import 'package:flutter/widgets.dart';

/// Lays [children] out in [columns] equal columns separated by [gap]. Used by the summary row of
/// indicators (`.stats`).
class ResponsiveGrid extends StatelessWidget {
  const ResponsiveGrid({super.key, required this.columns, required this.gap, required this.children});

  final int columns;
  final double gap;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = (constraints.maxWidth - gap * (columns - 1)) / columns;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: [for (final child in children) SizedBox(width: width, child: child)],
        );
      },
    );
  }
}
