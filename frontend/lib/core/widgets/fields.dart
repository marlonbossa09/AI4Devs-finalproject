import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_tokens.dart';
import '../utils/dates.dart';
import 'focus_ring.dart';

/// Label above an input (`.field label`).
class FieldLabel extends StatelessWidget {
  const FieldLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpace.xs + 2),
    child: Text(
      text,
      style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700, color: AppColors.textLabel),
    ),
  );
}

/// Text input with its label above it (`.field`).
class LabeledField extends StatelessWidget {
  const LabeledField({
    super.key,
    required this.label,
    this.controller,
    this.hint,
    this.hintBelow,
    this.errorText,
    this.enabled = true,
    this.obscure = false,
    this.minLines,
    this.maxLines = 1,
    this.autofillHints,
    this.textInputAction,
    this.onSubmitted,
    this.onChanged,
    this.fieldKey,
    this.suffix,
    this.focusNode,
  });

  final String label;
  final TextEditingController? controller;
  final String? hint;

  /// Small note under the input (`.hint`).
  final String? hintBelow;
  final String? errorText;
  final bool enabled;
  final bool obscure;
  final int? minLines;
  final int? maxLines;
  final Iterable<String>? autofillHints;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onSubmitted;
  final ValueChanged<String>? onChanged;

  /// Key of the inner text field, so tests and automation can find it.
  final Key? fieldKey;

  /// Focus node of the inner text field, for a form that decides where the focus starts.
  final FocusNode? focusNode;

  /// Widget at the end of the input (for example the show/hide button of a password).
  final Widget? suffix;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel(label),
        TextField(
          key: fieldKey,
          controller: controller,
          focusNode: focusNode,
          enabled: enabled,
          obscureText: obscure,
          minLines: minLines,
          maxLines: obscure ? 1 : maxLines,
          autofillHints: autofillHints,
          textInputAction: textInputAction,
          onSubmitted: onSubmitted,
          onChanged: onChanged,
          style: TextStyle(fontSize: AppType.body, color: enabled ? AppColors.fieldText : AppColors.textSecondary),
          decoration: InputDecoration(
            hintText: hint,
            errorText: errorText,
            suffixIcon: suffix,
            fillColor: enabled ? AppColors.white : AppColors.fieldDisabledBackground,
          ),
        ),
        if (hintBelow != null) ...[
          const SizedBox(height: AppSpace.sm),
          Text(hintBelow!, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
        ],
      ],
    );
  }
}

/// Date input that opens the calendar picker (`input type=date` in the design).
class DateField extends StatelessWidget {
  const DateField({
    super.key,
    required this.label,
    required this.date,
    required this.onChanged,
    this.fieldKey,
    this.firstDate,
    this.lastDate,
    this.errorText,
  });

  final String label;
  final DateTime date;
  final ValueChanged<DateTime> onChanged;
  final Key? fieldKey;

  /// Earliest date the picker offers (default: year 2000).
  final DateTime? firstDate;

  /// Latest date the picker offers (default: year 2100).
  final DateTime? lastDate;
  final String? errorText;

  Future<void> _pick(BuildContext context) async {
    final first = firstDate ?? DateTime(2000);
    final last = lastDate;
    var initial = date.isBefore(first) ? first : date;
    if (last != null && initial.isAfter(last)) initial = last;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: first,
      lastDate: last ?? DateTime(2100),
      helpText: label,
    );
    if (picked != null) onChanged(dateOnly(picked));
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel(label),
        Semantics(
          button: true,
          label: '$label ${formatShortDate(date)}',
          child: FocusRingInk(
            inkKey: fieldKey,
            onTap: () => _pick(context),
            child: Container(
              height: AppSize.control(context),
              padding: const EdgeInsets.symmetric(horizontal: AppSpace.md),
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(AppRadius.control),
                border: Border.all(color: errorText != null ? AppColors.error : AppColors.fieldBorder),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      formatShortDate(date),
                      style: const TextStyle(fontSize: AppType.body, color: AppColors.fieldText),
                    ),
                  ),
                  const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.muted),
                ],
              ),
            ),
          ),
        ),
        if (errorText != null) ...[
          const SizedBox(height: AppSpace.xs + 2),
          Text(errorText!, style: const TextStyle(fontSize: AppType.caption, color: AppColors.error)),
        ],
      ],
    );
  }
}

/// Dropdown with its label above it (a `select` in the design). [options] keeps its order.
class SelectField<T> extends StatelessWidget {
  const SelectField({
    super.key,
    required this.label,
    required this.options,
    required this.value,
    required this.onChanged,
    this.hint,
    this.errorText,
    this.enabled = true,
  });

  final String label;

  /// Option value -> label.
  final Map<T, String> options;
  final T? value;
  final ValueChanged<T?> onChanged;
  final String? hint;
  final String? errorText;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel(label),
        InputDecorator(
          isEmpty: value == null,
          decoration: InputDecoration(
            errorText: errorText,
            fillColor: enabled ? AppColors.white : AppColors.fieldDisabledBackground,
            contentPadding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.xs),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<T>(
              value: value,
              isExpanded: true,
              isDense: true,
              hint: hint == null
                  ? null
                  : Text(hint!, style: const TextStyle(fontSize: AppType.body, color: AppColors.textFaint)),
              icon: const Icon(Icons.expand_more, size: 18, color: AppColors.muted),
              style: const TextStyle(fontSize: AppType.body, color: AppColors.fieldText),
              borderRadius: BorderRadius.circular(AppRadius.control),
              items: [
                for (final entry in options.entries)
                  DropdownMenuItem<T>(
                    value: entry.key,
                    child: Text(entry.value, overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: enabled ? onChanged : null,
            ),
          ),
        ),
      ],
    );
  }
}
