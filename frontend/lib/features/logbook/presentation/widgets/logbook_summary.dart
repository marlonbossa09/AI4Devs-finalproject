import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../domain/entities/logbook_entities.dart';

String _dateTypeLabel(DateType type) => switch (type) {
  DateType.past => 'Jornada pasada',
  DateType.today => 'Jornada actual',
  DateType.future => 'Jornada futura',
};

/// Header of a persisted logbook: its state and its three dates apart (RN-18), and the summary.
class LogbookSummary extends StatelessWidget {
  const LogbookSummary({super.key, required this.logbook});

  final Logbook logbook;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              KeyedSubtree(
                key: const Key('logbook-state'),
                child: StatusPill(
                  label: logbook.closed ? 'Cerrada' : 'Abierta',
                  kind: logbook.closed ? PillKind.blocked : PillKind.done,
                ),
              ),
              StatusPill(label: _dateTypeLabel(logbook.dateType), kind: PillKind.progress),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 28,
            runSpacing: 10,
            children: [
              _DateItem(label: 'Fecha laboral', value: formatDate(logbook.date)),
              _DateItem(label: 'Registrada', value: formatDateTime(logbook.createdAt)),
              _DateItem(label: 'Modificada', value: formatDateTime(logbook.updatedAt)),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            logbook.summary.isEmpty ? 'Sin resumen' : logbook.summary,
            style: TextStyle(
              fontSize: 12,
              color: AppColors.textSoft,
              fontStyle: logbook.summary.isEmpty ? FontStyle.italic : FontStyle.normal,
            ),
          ),
        ],
      ),
    );
  }
}

class _DateItem extends StatelessWidget {
  const _DateItem({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textFaint)),
        const SizedBox(height: 3),
        Text(
          value,
          semanticsLabel: '$label: $value',
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textBody),
        ),
      ],
    );
  }
}
