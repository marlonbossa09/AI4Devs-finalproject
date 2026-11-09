import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import 'buttons.dart';

/// Asks the user to confirm an action that loses something (text typed and not saved). Resolves to
/// true when they confirm and to false when they choose to keep things as they are, press Escape or
/// tap outside. The safe option is the one that keeps the content, and it is the first one.
Future<bool> showConfirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
  required String cancelLabel,
  bool destructive = true,
  IconData icon = Icons.warning_amber_rounded,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => _ConfirmDialog(
      title: title,
      message: message,
      confirmLabel: confirmLabel,
      cancelLabel: cancelLabel,
      destructive: destructive,
      icon: icon,
    ),
  );
  return result ?? false;
}

class _ConfirmDialog extends StatelessWidget {
  const _ConfirmDialog({
    required this.title,
    required this.message,
    required this.confirmLabel,
    required this.cancelLabel,
    required this.destructive,
    required this.icon,
  });

  final String title;
  final String message;
  final String confirmLabel;
  final String cancelLabel;

  /// A destructive confirmation (it loses something) keeps the safe option as the main button; a
  /// plain one makes the confirmation the main button.
  final bool destructive;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final narrow = MediaQuery.sizeOf(context).width < 480;
    final keep = destructive
        ? PrimaryButton(
            key: const Key('confirm-keep'),
            label: cancelLabel,
            expand: narrow,
            onPressed: () => Navigator.of(context).pop(false),
          )
        : SizedBox(
            width: narrow ? double.infinity : null,
            child: SecondaryButton(
              key: const Key('confirm-keep'),
              label: cancelLabel,
              onPressed: () => Navigator.of(context).pop(false),
            ),
          );
    final discard = !destructive
        ? PrimaryButton(
            key: const Key('confirm-discard'),
            label: confirmLabel,
            expand: narrow,
            onPressed: () => Navigator.of(context).pop(true),
          )
        : OutlinedButton(
            key: const Key('confirm-discard'),
            onPressed: () => Navigator.of(context).pop(true),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.error,
              side: const BorderSide(color: AppColors.error),
              minimumSize: const Size(0, 44),
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              textStyle: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
            child: Text(confirmLabel),
          );
    return Dialog(
      backgroundColor: AppColors.white,
      insetPadding: const EdgeInsets.all(20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    icon,
                    size: 20,
                    color: destructive
                        ? AppColors.pendingText
                        : AppColors.primary,
                  ),
                  const SizedBox(width: 10),
                  Flexible(
                    child: Text(
                      title,
                      key: const Key('confirm-title'),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: AppColors.ink,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                message,
                key: const Key('confirm-message'),
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.6,
                  color: AppColors.textBody,
                ),
              ),
              const SizedBox(height: 22),
              if (narrow)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: destructive
                      ? [keep, const SizedBox(height: 10), discard]
                      : [discard, const SizedBox(height: 10), keep],
                )
              else
                Wrap(
                  alignment: WrapAlignment.end,
                  spacing: 10,
                  runSpacing: 10,
                  children: destructive ? [discard, keep] : [keep, discard],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
