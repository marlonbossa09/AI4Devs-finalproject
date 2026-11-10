import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/utils/keys.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/toast.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/mark_rules.dart';
import '../providers/logbook_notifier.dart';
import 'mark_dialogs.dart';

/// The action of the activity detail that marks the activity as registered by mistake (M3-05) or, once
/// marked, reverts that mark (M3-06). Nothing is shown when neither applies.
///
/// - Marking is offered only for an activity without progress after its origin day (RN-59); the server
///   still decides and its refusal is shown in the dialog.
/// - Both go through a dialog (the reason for marking; a confirmation for reverting), show loading and
///   ignore a second tap while they run.
/// - Each uses one idempotency key per intention: reused when retrying, renewed once the server accepts it.
/// - After the server answers, every cached day, the list and the detail are reloaded from the API.
class ActivityMarkActions extends ConsumerStatefulWidget {
  const ActivityMarkActions({super.key, required this.activity, required this.progress});

  final Activity activity;
  final List<Progress> progress;

  @override
  ConsumerState<ActivityMarkActions> createState() => _ActivityMarkActionsState();
}

class _ActivityMarkActionsState extends ConsumerState<ActivityMarkActions> {
  final _markIntention = IntentionKey();
  final _revertIntention = IntentionKey();

  Future<void> _mark() async {
    final activity = widget.activity;
    final provider = logbookProvider(activity.date);
    final marked = await showMarkErrorDialog(
      context,
      activityTitle: activity.title,
      onSubmit: (reason) async {
        final key = _markIntention.forRequest('${activity.id}|$reason');
        // Held at container level, so it survives even if this widget is unmounted meanwhile
        final keepAlive = ProviderScope.containerOf(context, listen: false).listen(provider, (previous, next) {});
        try {
          await ref.read(provider.notifier).markAsError(activityId: activity.id, reason: reason, key: key);
          _markIntention.accepted();
        } finally {
          keepAlive.close();
        }
      },
    );
    if (marked && mounted) showToast(context, 'Actividad marcada como registrada por error.');
  }

  Future<void> _revert() async {
    final activity = widget.activity;
    final provider = logbookProvider(activity.date);
    final reverted = await showRevertMarkDialog(
      context,
      activityTitle: activity.title,
      onSubmit: () async {
        final key = _revertIntention.forRequest(activity.id);
        final keepAlive = ProviderScope.containerOf(context, listen: false).listen(provider, (previous, next) {});
        try {
          await ref.read(provider.notifier).revertMark(activityId: activity.id, key: key);
          _revertIntention.accepted();
        } finally {
          keepAlive.close();
        }
      },
    );
    if (reverted && mounted) showToast(context, 'Marca de error revertida.');
  }

  @override
  Widget build(BuildContext context) {
    final activity = widget.activity;
    if (canRevertMark(activity)) {
      return SecondaryButton(
        key: const Key('detail-revert-mark'),
        label: 'Revertir marca',
        onPressed: _revert,
      );
    }
    if (canMarkAsError(activity: activity, progress: widget.progress)) {
      return SecondaryButton(
        key: const Key('detail-mark-error'),
        label: 'Marcar como registrada por error',
        onPressed: _mark,
      );
    }
    return const SizedBox.shrink();
  }
}
