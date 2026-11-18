import 'package:flutter/material.dart';

import '../../../../core/errors/error_messages.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../providers/team_data.dart';
import 'peer_logbook_view.dart' show FieldCaption;
import 'shared_activity_tile.dart';

/// The history (M4-02): one card per logbook the user may read, in the order the server sends (date, person), and a
/// "load more" that follows the server cursor. It is read-only. [nameOf] turns a person id into what to show; an
/// id that is not in the current team list (someone who already left) is shown without a name: the client has none.
class HistoryList extends StatelessWidget {
  const HistoryList({super.key, required this.history, required this.nameOf, required this.onLoadMore});

  final HistoryViewState history;
  final String Function(String personId) nameOf;
  final VoidCallback onLoadMore;

  @override
  Widget build(BuildContext context) {
    if (history.items.isEmpty) {
      return const EmptyState(
        'No hay bitácoras que puedas leer en ese rango.',
        key: Key('history-empty'),
      );
    }
    return Column(
      key: const Key('history-list'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final entry in history.items)
          Container(
            key: Key('history-entry-${entry.ownerId}-${formatDate(entry.date)}'),
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFAFBFD),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 10,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(nameOf(entry.ownerId), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
                    Text(formatLongDate(entry.date), style: const TextStyle(fontSize: 12, color: AppColors.textSoft)),
                    StatusPill(label: entry.closed ? 'Cerrada' : 'Abierta', kind: entry.closed ? PillKind.done : PillKind.progress),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  entry.summary.trim().isEmpty ? 'Sin resumen.' : entry.summary,
                  style: TextStyle(fontSize: 12.5, height: 1.5, color: entry.summary.trim().isEmpty ? AppColors.textFaint : AppColors.textBody),
                ),
                if (entry.activities.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  const FieldCaption('Actividades'),
                  const SizedBox(height: 6),
                  for (final activity in entry.activities) SharedActivityTile(activity: activity),
                ],
              ],
            ),
          ),
        if (history.hasMore || history.moreError != null) ...[
          if (history.moreError != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                errorMessage(history.moreError!),
                key: const Key('history-more-error'),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: AppColors.error),
              ),
            ),
          Center(
            child: SecondaryButton(
              key: const Key('history-load-more'),
              label: history.loadingMore ? 'Cargando…' : (history.moreError != null ? 'Reintentar' : 'Ver más'),
              onPressed: history.loadingMore ? null : onLoadMore,
            ),
          ),
        ],
      ],
    );
  }
}
