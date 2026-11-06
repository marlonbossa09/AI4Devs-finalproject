import 'package:flutter/material.dart';

import '../../domain/entities/logbook_entities.dart';

/// Colors used to tell an UNPLANNED activity apart from a planned one. They are deliberately not
/// those of any status pill: being unplanned is an identification, not a status (RN-20, CA-57).
class UnplannedColors {
  const UnplannedColors._();

  static const background = Color(0xFFF1EEFB);
  static const foreground = Color(0xFF6B5BB0);
}

/// Small tag "No planificada". It is shown only for activities registered without a prior planning;
/// planned activities carry no tag.
class OriginTag extends StatelessWidget {
  const OriginTag({super.key, required this.origin});

  final ActivityOrigin origin;

  @override
  Widget build(BuildContext context) {
    if (origin != ActivityOrigin.unplanned) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: UnplannedColors.background, borderRadius: BorderRadius.circular(6)),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.bolt, size: 11, color: UnplannedColors.foreground),
          SizedBox(width: 3),
          Text(
            'No planificada',
            style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: UnplannedColors.foreground),
          ),
        ],
      ),
    );
  }
}
