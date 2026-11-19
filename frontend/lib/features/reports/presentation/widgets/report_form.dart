import 'package:flutter/material.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';

/// The request of a report in one compact card: who (only the individual report of a supervisor), the period and the button, in
/// one line when there is room, then the one-line note of limits and, if the period is certain to be rejected, why.
///
/// While a generation runs the form cannot be changed (no pointer and no keyboard focus): nothing to cancel, nothing to mix up.
class ReportForm extends StatelessWidget {
  const ReportForm({
    super.key,
    required this.fromKey,
    required this.toKey,
    required this.from,
    required this.to,
    required this.onFromChanged,
    required this.onToChanged,
    required this.hint,
    required this.hintKey,
    required this.submitKey,
    required this.submitLabel,
    required this.busy,
    required this.onSubmit,
    this.rangeError,
    this.leading,
  });

  final Key fromKey;
  final Key toKey;
  final DateTime from;
  final DateTime to;
  final ValueChanged<DateTime> onFromChanged;
  final ValueChanged<DateTime> onToChanged;
  final String hint;
  final Key hintKey;
  final Key submitKey;
  final String submitLabel;
  final bool busy;
  final VoidCallback onSubmit;

  /// Why the period was not sent (shown under the form, with its icon and words), or null.
  final String? rangeError;

  /// A field before the period (the person selector).
  final Widget? leading;

  static const double _dateWidth = 176;
  static const double _leadingWidth = 280;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    // Two dates side by side need about 150 px each at the normal size; with a large text size they go one under the other
    final largeText = MediaQuery.textScalerOf(context).scale(AppType.body) / AppType.body > 1.3;
    return AppCard(
      padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xl),
      child: ExcludeFocus(
        excluding: busy,
        child: IgnorePointer(
          ignoring: busy,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth;
              final narrow = width < 560;
              final dateWidth = narrow ? (largeText ? width : (width - AppSpace.md) / 2) : _dateWidth;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Wrap(
                    spacing: AppSpace.md,
                    runSpacing: AppSpace.md,
                    crossAxisAlignment: WrapCrossAlignment.end,
                    children: [
                      if (leading != null) SizedBox(width: narrow ? width : _leadingWidth, child: leading),
                      SizedBox(
                        width: dateWidth,
                        child: DateField(fieldKey: fromKey, label: 'Desde', date: from, onChanged: onFromChanged),
                      ),
                      SizedBox(
                        width: dateWidth,
                        child: DateField(fieldKey: toKey, label: 'Hasta', date: to, onChanged: onToChanged),
                      ),
                      SizedBox(
                        width: narrow ? width : null,
                        child: PrimaryButton(
                          key: submitKey,
                          label: busy ? 'Generando…' : submitLabel,
                          icon: Icons.summarize_outlined,
                          loading: busy,
                          expand: narrow,
                          onPressed: busy ? null : onSubmit,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpace.md),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(padding: EdgeInsets.only(top: 1), child: Icon(Icons.info_outline, size: 14, color: AppColors.textFaint)),
                      const SizedBox(width: AppSpace.sm),
                      Expanded(child: Text(hint, key: hintKey, style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textFaint))),
                    ],
                  ),
                  // A polite live region: a screen reader says why the period was not sent
                  Semantics(
                    liveRegion: true,
                    container: true,
                    child: rangeError == null
                        ? const SizedBox.shrink()
                        : Padding(
                            padding: const EdgeInsets.only(top: AppSpace.sm),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Padding(padding: EdgeInsets.only(top: 1), child: Icon(Icons.error_outline, size: 16, color: AppColors.error)),
                                const SizedBox(width: AppSpace.sm),
                                Expanded(
                                  child: Text(rangeError!, style: const TextStyle(fontSize: AppType.caption, height: 1.4, fontWeight: FontWeight.w700, color: AppColors.error)),
                                ),
                              ],
                            ),
                          ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
