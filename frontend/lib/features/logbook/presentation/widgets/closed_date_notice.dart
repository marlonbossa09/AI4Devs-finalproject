import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';

/// Tells the user that the logbook of the chosen date is closed, so nothing can be registered in it
/// (RN-108, CA-284). The forms show it and do not offer to send: the user can pick another date or
/// reopen the day from Mi bitácora. The server still rejects the write, whatever the screen does.
class ClosedDateNotice extends StatelessWidget {
  const ClosedDateNotice({super.key, required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('closed-date-notice'),
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7F6),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: const Color(0xFFF3D3D0)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 1),
            child: Icon(Icons.lock_outline, size: 15, color: AppColors.blockedText),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'La jornada del ${formatShortDate(date)} está cerrada, así que no admite nuevos registros. '
              'Elige otra fecha, o reábrela desde Mi bitácora indicando un motivo.',
              style: const TextStyle(fontSize: 12, height: 1.55, color: AppColors.blockedText),
            ),
          ),
        ],
      ),
    );
  }
}
