import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import 'form_parts.dart';

/// Shared frame of the dialogs that ask for a reason or a confirmation before changing a record (reopening a day, marking an
/// activity as registered by mistake, reverting that mark): title with its icon, an explanation, an optional field, the error
/// the server may answer, and the buttons (stacked on a narrow screen, the main action first).
///
/// While [saving] the dialog cannot be dismissed.
class ActionDialogFrame extends StatelessWidget {
  const ActionDialogFrame({
    super.key,
    required this.saving,
    required this.icon,
    required this.title,
    required this.titleKey,
    required this.intro,
    required this.cancel,
    required this.submit,
    this.field,
    this.error,
    this.errorKey,
  });

  final bool saving;
  final IconData icon;
  final String title;
  final Key titleKey;
  final String intro;
  final Widget cancel;
  final Widget submit;
  final Widget? field;
  final String? error;
  final Key? errorKey;

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 480;
    return PopScope(
      canPop: !saving,
      child: Dialog(
        backgroundColor: AppColors.white,
        insetPadding: const EdgeInsets.all(AppSpace.xl),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.panel)),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpace.xxl),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    ExcludeSemantics(child: Icon(icon, size: 20, color: AppColors.primary)),
                    const SizedBox(width: AppSpace.md),
                    Flexible(
                      child: Text(
                        title,
                        key: titleKey,
                        style: const TextStyle(fontSize: AppType.cardTitle, fontWeight: FontWeight.w800, color: AppColors.ink),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.md),
                Text(intro, style: const TextStyle(fontSize: AppType.body, height: 1.5, color: AppColors.textBody)),
                if (field != null) ...[const SizedBox(height: AppSpace.lg), field!],
                if (error != null) ...[const SizedBox(height: AppSpace.md), FormErrorText(error!, textKey: errorKey)],
                const SizedBox(height: AppSpace.xl),
                if (narrow)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [submit, const SizedBox(height: AppSpace.sm), SizedBox(width: double.infinity, child: cancel)],
                  )
                else
                  Wrap(alignment: WrapAlignment.end, spacing: AppSpace.sm, runSpacing: AppSpace.sm, children: [cancel, submit]),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
