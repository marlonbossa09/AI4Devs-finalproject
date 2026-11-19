import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
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

/// Width from which the dates and the action of the period sit on one line.
const double _widePeriodMinWidth = 620;

/// The supervisor's consolidated view of the team in a period (M4-03). Read-only: it asks, it shows and its only action
/// opens the history of an activity (M4-04). It decides nothing about permissions: if the server says no, it says no.
///
/// Reading order: the period (and what "al corte" means), the summary of the period by status at the cut, and the
/// activities, each with its status at the cut and, apart, its current status.
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
    final pad = mobile ? AppSpace.lg : AppSpace.xl;
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    final selection = ref.watch(supervisionSelectionProvider);
    final from = selection.from ?? addDays(today, -6);
    final to = selection.to ?? today;

    Widget body;
    if (session != null && session.role != Role.supervisor) {
      // Unreachable from the menu (it offers nothing to a collaborator); the server would answer 403 in any case.
      body = AppCard(
        padding: EdgeInsets.all(pad),
        child: const EmptyState('Esta vista es solo para la supervisión del equipo.', key: Key('supervision-not-available')),
      );
    } else {
      body = _form(session?.user.id, from, to, selection.query, pad);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Supervisión',
          title: 'Supervisión del equipo',
          subtitle: 'Las actividades de tu equipo en un período, con su estado al corte y, aparte, su estado actual.',
        ),
        body,
      ],
    );
  }

  Widget _form(String? myId, DateTime from, DateTime to, ({DateTime from, DateTime to})? query, double pad) {
    final members = ref.watch(teamMembersProvider).value ?? const [];
    String nameOf(String id) {
      if (id == myId) return 'Tú';
      for (final member in members) {
        if (member.id == id) return member.name;
      }
      // Not in the current team: the client holds no name for them (D-M4-02, limitation).
      return 'Persona que ya no está en tu equipo';
    }

    final fromField = DateField(
      fieldKey: const Key('supervision-from'),
      label: 'Desde',
      date: from,
      onChanged: (date) {
        setState(() => _rangeError = null);
        ref.read(supervisionSelectionProvider.notifier).setFrom(date);
      },
    );
    final toField = DateField(
      fieldKey: const Key('supervision-to'),
      label: 'Hasta',
      date: to,
      errorText: _rangeError,
      onChanged: (date) {
        setState(() => _rangeError = null);
        ref.read(supervisionSelectionProvider.notifier).setTo(date);
      },
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppCard(
          padding: EdgeInsets.all(pad),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const PanelHeader(title: 'Período', bottom: AppSpace.md),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= _widePeriodMinWidth;
                  final submit = PrimaryButton(
                    key: const Key('supervision-submit'),
                    label: 'Ver supervisión',
                    expand: !wide,
                    onPressed: () => _submit(from, to),
                  );
                  if (!wide) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [Expanded(child: fromField), const SizedBox(width: AppSpace.md), Expanded(child: toField)],
                        ),
                        const SizedBox(height: AppSpace.md),
                        submit,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 200, child: fromField),
                      const SizedBox(width: AppSpace.md),
                      SizedBox(width: 200, child: toField),
                      const SizedBox(width: AppSpace.md),
                      _BesideFields(child: submit),
                    ],
                  );
                },
              ),
              const SizedBox(height: AppSpace.md),
              const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: EdgeInsets.only(top: 2),
                    child: ExcludeSemantics(child: Icon(Icons.info_outline, size: 14, color: AppColors.textSoft)),
                  ),
                  SizedBox(width: AppSpace.sm),
                  Expanded(
                    child: Text(
                      'El período es obligatorio y abarca como máximo $maxHistoryRangeDays días. El estado «al corte» es el que tenían las actividades '
                      'el último día del período.',
                      key: Key('supervision-hint'),
                      style: TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        if (query == null)
          AppCard(
            padding: EdgeInsets.all(pad),
            child: const EmptyState('Elige un período para ver las actividades de tu equipo.', key: Key('supervision-none')),
          )
        else
          _SupervisionResult(from: query.from, to: query.to, nameOf: nameOf, pad: pad),
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

/// Puts an action on the same baseline as the fields beside it: it reserves the height of a field label above the action.
class _BesideFields extends StatelessWidget {
  const _BesideFields({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Visibility(visible: false, maintainSize: true, maintainAnimation: true, maintainState: true, child: FieldLabel('Desde')),
        child,
      ],
    );
  }
}

class _SupervisionResult extends ConsumerWidget {
  const _SupervisionResult({required this.from, required this.to, required this.nameOf, required this.pad});

  final DateTime from;
  final DateTime to;
  final String Function(String) nameOf;
  final double pad;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(supervisionFeedProvider(from, to));
    if (result.isLoading) {
      return AppCard(
        child: Padding(
          key: const Key('supervision-loading'),
          padding: const EdgeInsets.all(AppSpace.xxl + AppSpace.sm),
          child: const Center(child: CircularProgressIndicator(semanticsLabel: 'Cargando la supervisión')),
        ),
      );
    }
    if (result.hasError) {
      final error = result.error;
      return AppCard(
        padding: EdgeInsets.symmetric(horizontal: pad),
        child: ErrorBox(
          message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la supervisión.',
          onRetry: () => ref.invalidate(supervisionFeedProvider(from, to)),
        ),
      );
    }
    final feed = result.value!;
    final loaded = feed.items.length;
    return Column(
      key: const Key('supervision-result'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppCard(
          padding: EdgeInsets.all(pad),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // A polite live region: when the period is asked again a screen reader says which period and which cut it is.
              Semantics(
                liveRegion: true,
                child: Padding(
                  padding: const EdgeInsets.only(bottom: AppSpace.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Semantics(header: true, child: Text('Resumen del período', style: context.heading(AppType.cardTitle))),
                      const SizedBox(height: AppSpace.xs),
                      Text(
                        'Período del ${formatShortDate(feed.first.from)} al ${formatShortDate(feed.first.to)}. Corte: ${formatShortDate(feed.first.cut)}.',
                        key: const Key('supervision-period'),
                        style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
                      ),
                    ],
                  ),
                ),
              ),
              SupervisionTotals(page: feed.first),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.lg),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: EdgeInsets.fromLTRB(pad, pad, pad, feed.items.isEmpty ? pad : AppSpace.xs),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const PanelHeader(
                      title: 'Actividades del período',
                      subtitle: 'Estado al corte de cada una y, aparte, su estado actual cuando es distinto',
                      bottom: AppSpace.xs,
                    ),
                    if (feed.items.isEmpty)
                      const EmptyState('No hay actividades de tu equipo en ese período.', key: Key('supervision-empty')),
                  ],
                ),
              ),
              if (feed.items.isNotEmpty)
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: pad),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (var i = 0; i < feed.items.length; i++)
                        SupervisionItemTile(
                          first: i == 0,
                          item: feed.items[i],
                          ownerName: nameOf(feed.items[i].ownerId),
                          onOpen: () {
                            ref.read(supervisionActivityTargetProvider.notifier).select(feed.items[i].activity.id);
                            ref.read(currentPageProvider.notifier).go(AppPage.supervisionActivity);
                          },
                        ),
                    ],
                  ),
                ),
              if (feed.items.isNotEmpty || feed.moreError != null || feed.hasMore) ...[
                if (feed.moreError != null)
                  Padding(
                    padding: EdgeInsets.fromLTRB(pad, AppSpace.sm, pad, AppSpace.sm),
                    child: Text(
                      errorMessage(feed.moreError!),
                      key: const Key('supervision-more-error'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: AppType.caption, color: AppColors.error),
                    ),
                  ),
                PanelFooter(
                  text: feed.hasMore || feed.moreError != null ? '$loaded elementos cargados · hay más' : '$loaded elementos en esta vista',
                  action: feed.hasMore || feed.moreError != null
                      ? SecondaryButton(
                          key: const Key('supervision-load-more'),
                          label: feed.loadingMore ? 'Cargando…' : (feed.moreError != null ? 'Reintentar' : 'Ver más'),
                          onPressed: feed.loadingMore ? null : () => ref.read(supervisionFeedProvider(from, to).notifier).loadMore(),
                        )
                      : null,
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
