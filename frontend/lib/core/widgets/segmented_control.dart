import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Small switch between a few options (`.segmented`).
class SegmentedControl<T> extends StatelessWidget {
  const SegmentedControl({
    super.key,
    required this.options,
    required this.selected,
    required this.onChanged,
  });

  /// Option value -> label.
  final Map<T, String> options;
  final T selected;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F6FA),
        borderRadius: BorderRadius.circular(9),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final entry in options.entries)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1.5),
              child: Material(
                color: entry.key == selected ? AppColors.white : Colors.transparent,
                elevation: entry.key == selected ? 1.5 : 0,
                shadowColor: const Color(0x14102F45),
                borderRadius: BorderRadius.circular(7),
                child: InkWell(
                  borderRadius: BorderRadius.circular(7),
                  onTap: () => onChanged(entry.key),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                    child: Text(
                      entry.value,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: entry.key == selected ? FontWeight.w800 : FontWeight.w400,
                        color: entry.key == selected ? AppColors.textStrong : const Color(0xFF77859B),
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
