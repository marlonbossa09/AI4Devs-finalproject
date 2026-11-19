import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';

/// Tells the user that the logbook of the chosen date is closed, so nothing can be registered in it
/// (RN-108, CA-284). The forms show it and do not offer to send: the user can pick another date or
/// reopen the day from Mi bitácora. The server still rejects the write, whatever the screen does.
class ClosedDateNotice extends StatelessWidget {
  const ClosedDateNotice({super.key, required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    return ClosedDayBox(
      boxKey: const Key('closed-date-notice'),
      text:
          'La jornada del ${formatShortDate(date)} está cerrada, así que no admite nuevos registros. '
          'Elige otra fecha, o reábrela desde Mi bitácora indicando un motivo.',
    );
  }
}

/// The red box with a lock that says a day is closed. Its message is the caller's, because what the day forbids depends on the form.
class ClosedDayBox extends StatelessWidget {
  const ClosedDayBox({super.key, required this.text, this.boxKey});

  final String text;

  /// Key of the box, so tests and automation can find it.
  final Key? boxKey;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: boxKey,
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColors.blockedBackground,
        borderRadius: BorderRadius.circular(AppRadius.control + 2),
        border: Border.all(color: AppColors.blockedText.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 1),
            child: ExcludeSemantics(child: Icon(Icons.lock_outline, size: 16, color: AppColors.blockedText)),
          ),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(text, style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.blockedText)),
          ),
        ],
      ),
    );
  }
}
