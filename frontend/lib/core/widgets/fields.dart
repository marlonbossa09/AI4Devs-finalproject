import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../utils/dates.dart';

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);

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

  /// Key of the inner text field, so tests and automation can find it.
  final Key? fieldKey;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FieldLabel(label),
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
  });

  final String label;
  final DateTime date;
  final ValueChanged<DateTime> onChanged;
  final Key? fieldKey;

  Future<void> _pick(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: date,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: label,
    );
    if (picked != null) onChanged(dateOnly(picked));
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FieldLabel(label),
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
      ],
    );
  }
}
