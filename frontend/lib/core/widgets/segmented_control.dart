import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_tokens.dart';
import 'focus_ring.dart';

/// Small switch between a few options (`.segmented`). Each option is announced as a button of a mutually exclusive group,
/// with its selected state; the selected one is also told by weight and by a white "raised" background, not only by color.
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
      padding: const EdgeInsets.all(AppSpace.xs),
      decoration: BoxDecoration(
        color: const Color(0xFFEEF2F7),
        borderRadius: BorderRadius.circular(AppRadius.control + 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final entry in options.entries)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1.5),
              child: Semantics(
                button: true,
                selected: entry.key == selected,
                inMutuallyExclusiveGroup: true,
                label: entry.value,
                excludeSemantics: true,
                onTap: () => onChanged(entry.key),
                child: Material(
                  color: entry.key == selected ? AppColors.white : Colors.transparent,
                  elevation: entry.key == selected ? 1.5 : 0,
                  shadowColor: const Color(0x14102F45),
                  borderRadius: BorderRadius.circular(AppRadius.control - 1),
                  child: FocusRingInk(
                    borderRadius: BorderRadius.circular(AppRadius.control - 1),
                    onTap: () => onChanged(entry.key),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: AppSize.minTouch - AppSpace.sm),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm),
                        child: Center(
                          widthFactor: 1,
                          child: Text(
                            entry.value,
                            style: TextStyle(
                              fontSize: AppType.caption,
                              fontWeight: entry.key == selected ? FontWeight.w800 : FontWeight.w600,
                              color: entry.key == selected ? AppColors.ink : AppColors.muted,
                            ),
                          ),
                        ),
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
