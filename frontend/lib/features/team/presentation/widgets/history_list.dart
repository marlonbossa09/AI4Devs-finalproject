import 'package:flutter/material.dart';

import '../../../../core/errors/error_messages.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../providers/team_data.dart';
import 'peer_logbook_view.dart' show FieldCaption;
import 'shared_activity_tile.dart';

/// The history (M4-02): one block per logbook the user may read, in the order the server sends (date, person), and a
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
      return const EmptyState('No hay bitácoras que puedas leer en ese rango.', key: Key('history-empty'));
    }
    return Column(
      key: const Key('history-list'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final entry in history.items)
          Container(
            key: Key('history-entry-${entry.ownerId}-${formatDate(entry.date)}'),
            margin: const EdgeInsets.only(bottom: AppSpace.md),
            padding: const EdgeInsets.all(AppSpace.md),
            decoration: BoxDecoration(
              color: AppColors.panelFooter,
              borderRadius: BorderRadius.circular(AppRadius.card),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Semantics(
                  header: true,
                  label: '${nameOf(entry.ownerId)}, ${formatLongDate(entry.date)}, ${entry.closed ? 'cerrada' : 'abierta'}',
                  excludeSemantics: true,
                  child: Wrap(
                    spacing: AppSpace.md,
                    runSpacing: AppSpace.xs,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        nameOf(entry.ownerId),
                        style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink),
                      ),
                      Text(formatLongDate(entry.date), style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
                      StatusPill(
                        label: entry.closed ? 'Cerrada' : 'Abierta',
                        kind: entry.closed ? PillKind.done : PillKind.progress,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpace.sm),
                Text(
                  entry.summary.trim().isEmpty ? 'Sin resumen.' : entry.summary,
                  style: TextStyle(
                    fontSize: AppType.body,
                    height: 1.5,
                    color: entry.summary.trim().isEmpty ? AppColors.textSoft : AppColors.textBody,
                  ),
                ),
                if (entry.activities.isNotEmpty) ...[
                  const SizedBox(height: AppSpace.md),
                  const FieldCaption('Actividades'),
                  for (var i = 0; i < entry.activities.length; i++)
                    SharedActivityTile(first: i == 0, activity: entry.activities[i]),
                ],
              ],
            ),
          ),
        if (history.hasMore || history.moreError != null) ...[
          if (history.moreError != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpace.sm),
              child: Text(
                errorMessage(history.moreError!),
                key: const Key('history-more-error'),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: AppType.caption, color: AppColors.error),
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
