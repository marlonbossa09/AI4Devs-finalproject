import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/domain/entities/session.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../../logbook/presentation/providers/navigation.dart';
import '../../../team/domain/rules/history_range_rules.dart';
import '../../../team/presentation/providers/team_data.dart';
import '../providers/supervision_data.dart';
import '../providers/supervision_navigation.dart';
import '../widgets/supervision_item_tile.dart';

/// The supervisor's consolidated view of the team in a period (M4-03). Read-only: it asks, it shows and its only action
/// opens the history of an activity (M4-04). It decides nothing about permissions: if the server says no, it says no.
///
/// The cut of "status at the cut" is the LAST DAY of the period (there is no separate cut). The status at the cut and
/// the current status are shown apart and each only when the server reports it; the client never infers one from the
/// other. There is no ranking, score or comparison of people anywhere: only activities and counts of activities.
class SupervisionPage extends ConsumerStatefulWidget {
  const SupervisionPage({super.key});

  @override
  ConsumerState<SupervisionPage> createState() => _SupervisionPageState();
}

class _SupervisionPageState extends ConsumerState<SupervisionPage> {
  String? _rangeError;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    final selection = ref.watch(supervisionSelectionProvider);
    final from = selection.from ?? addDays(today, -6);
    final to = selection.to ?? today;

    Widget body;
    if (session != null && session.role != Role.supervisor) {
      // Unreachable from the menu (it offers nothing to a collaborator); the server would answer 403 in any case.
      body = const EmptyState('Esta vista es solo para la supervisión del equipo.', key: Key('supervision-not-available'));
    } else {
      body = _form(session?.user.id, from, to, selection.query);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Supervisión',
          title: 'Supervisión del equipo',
          subtitle: 'Las actividades de tu equipo en un período, con su estado al corte y, aparte, su estado actual.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 860),
            child: AppCard(padding: EdgeInsets.all(mobile ? 18 : 24), child: body),
          ),
        ),
      ],
    );
  }

  Widget _form(String? myId, DateTime from, DateTime to, ({DateTime from, DateTime to})? query) {
    final members = ref.watch(teamMembersProvider).value ?? const [];
    String nameOf(String id) {
      if (id == myId) return 'Tú';
      for (final member in members) {
        if (member.id == id) return member.name;
      }
      // Not in the current team: the client holds no name for them (D-M4-02, limitation).
      return 'Persona que ya no está en tu equipo';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('supervision-from'),
                label: 'Desde',
                date: from,
                onChanged: (date) {
                  setState(() => _rangeError = null);
                  ref.read(supervisionSelectionProvider.notifier).setFrom(date);
                },
              ),
            ),
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('supervision-to'),
                label: 'Hasta',
                date: to,
                errorText: _rangeError,
                onChanged: (date) {
                  setState(() => _rangeError = null);
                  ref.read(supervisionSelectionProvider.notifier).setTo(date);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'El período es obligatorio y abarca como máximo $maxHistoryRangeDays días. El estado «al corte» es el que tenían las actividades '
          'el último día del período.',
          key: const Key('supervision-hint'),
          style: const TextStyle(fontSize: 11, height: 1.5, color: AppColors.textFaint),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: PrimaryButton(key: const Key('supervision-submit'), label: 'Ver supervisión', onPressed: () => _submit(from, to)),
        ),
        const SizedBox(height: 18),
        if (query == null)
          const EmptyState('Elige un período para ver las actividades de tu equipo.', key: Key('supervision-none'))
        else
          _SupervisionResult(from: query.from, to: query.to, nameOf: nameOf),
      ],
    );
  }

  void _submit(DateTime from, DateTime to) {
    final problem = historyRangeProblem(from, to);
    if (problem != null) {
      // Not sent: the period is certain to be rejected (the server would say so anyway)
      setState(() => _rangeError = historyRangeMessage(problem));
      ref.read(supervisionSelectionProvider.notifier).clearQuery();
      return;
    }
    setState(() => _rangeError = null);
    // Asking is always asking the server again (see the team page): nothing loaded before stays on screen after a rejection
    ref.invalidate(supervisionFeedProvider(from, to));
    ref.read(supervisionSelectionProvider.notifier).ask(from, to);
  }
}

class _SupervisionResult extends ConsumerWidget {
  const _SupervisionResult({required this.from, required this.to, required this.nameOf});

  final DateTime from;
  final DateTime to;
  final String Function(String) nameOf;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(supervisionFeedProvider(from, to));
    if (result.isLoading) {
      return const Padding(
        key: Key('supervision-loading'),
        padding: EdgeInsets.all(28),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (result.hasError) {
      final error = result.error;
      return ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la supervisión.',
        onRetry: () => ref.invalidate(supervisionFeedProvider(from, to)),
      );
    }
    final feed = result.value!;
    return Column(
      key: const Key('supervision-result'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Período del ${formatShortDate(feed.first.from)} al ${formatShortDate(feed.first.to)}. Corte: ${formatShortDate(feed.first.cut)}.',
          key: const Key('supervision-period'),
          style: const TextStyle(fontSize: 12, color: AppColors.textSoft),
        ),
        const SizedBox(height: 12),
        SupervisionTotals(page: feed.first),
        const SizedBox(height: 18),
        if (feed.items.isEmpty)
          const EmptyState('No hay actividades de tu equipo en ese período.', key: Key('supervision-empty'))
        else
          for (final item in feed.items)
            SupervisionItemTile(
              item: item,
              ownerName: nameOf(item.ownerId),
              onOpen: () {
                ref.read(supervisionActivityTargetProvider.notifier).select(item.activity.id);
                ref.read(currentPageProvider.notifier).go(AppPage.supervisionActivity);
              },
            ),
        if (feed.hasMore || feed.moreError != null) ...[
          if (feed.moreError != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                errorMessage(feed.moreError!),
                key: const Key('supervision-more-error'),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: AppColors.error),
              ),
            ),
          Center(
            child: SecondaryButton(
              key: const Key('supervision-load-more'),
              label: feed.loadingMore ? 'Cargando…' : (feed.moreError != null ? 'Reintentar' : 'Ver más'),
              onPressed: feed.loadingMore ? null : () => ref.read(supervisionFeedProvider(from, to).notifier).loadMore(),
            ),
          ),
        ],
      ],
    );
  }
}
