import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../utils/dates.dart';

/// Label above an input (`.field label`).
class FieldLabel extends StatelessWidget {
  const FieldLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      text,
      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textLabel),
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

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FieldLabel(label),
        TextField(
          key: fieldKey,
          controller: controller,
          enabled: enabled,
          obscureText: obscure,
          minLines: minLines,
          maxLines: obscure ? 1 : maxLines,
          autofillHints: autofillHints,
          textInputAction: textInputAction,
          onSubmitted: onSubmitted,
          onChanged: onChanged,
          style: const TextStyle(fontSize: 13, color: AppColors.fieldText),
          decoration: InputDecoration(
            hintText: hint,
            errorText: errorText,
            fillColor: enabled ? AppColors.white : const Color(0xFFF3F6FA),
          ),
        ),
        if (hintBelow != null) ...[
          const SizedBox(height: 8),
          Text(hintBelow!, style: const TextStyle(fontSize: 11, color: Color(0xFF7E8DA1))),
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
    this.lastDate,
    this.errorText,
  });

  final String label;
  final DateTime date;
  final ValueChanged<DateTime> onChanged;
  final Key? fieldKey;

  /// Latest date the picker offers (default: year 2100).
  final DateTime? lastDate;
  final String? errorText;

  Future<void> _pick(BuildContext context) async {
    final last = lastDate;
    final picked = await showDatePicker(
      context: context,
      initialDate: last != null && date.isAfter(last) ? last : date,
      firstDate: DateTime(2000),
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
          child: InkWell(
            key: fieldKey,
            borderRadius: BorderRadius.circular(10),
            onTap: () => _pick(context),
            child: Container(
              height: 46,
              padding: const EdgeInsets.symmetric(horizontal: 13),
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.fieldBorder),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      formatShortDate(date),
                      style: const TextStyle(fontSize: 13, color: AppColors.fieldText),
                    ),
                  ),
                  const Icon(Icons.calendar_today_outlined, size: 16, color: Color(0xFF728097)),
                ],
              ),
            ),
          ),
        ),
        if (errorText != null) ...[
          const SizedBox(height: 6),
          Text(errorText!, style: const TextStyle(fontSize: 12, color: AppColors.error)),
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
            fillColor: enabled ? AppColors.white : const Color(0xFFF3F6FA),
            contentPadding: const EdgeInsets.symmetric(horizontal: 13, vertical: 2),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<T>(
              value: value,
              isExpanded: true,
              hint: hint == null
                  ? null
                  : Text(hint!, style: const TextStyle(fontSize: 13, color: AppColors.textFaint)),
              icon: const Icon(Icons.expand_more, size: 18, color: Color(0xFF728097)),
              style: const TextStyle(fontSize: 13, color: AppColors.fieldText),
              borderRadius: BorderRadius.circular(10),
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
