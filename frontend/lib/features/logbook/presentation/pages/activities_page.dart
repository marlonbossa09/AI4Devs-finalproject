import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/focus_ring.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/activity_list.dart';
import '../providers/navigation.dart';
import '../widgets/activity_tile.dart';
import '../widgets/form_parts.dart';
import '../widgets/new_activity_panel.dart';
import '../widgets/origin_tag.dart';
import '../widgets/status_choice.dart';

/// All the user's activities (M2-08), newest first, filtered by current status and loaded one page
/// at a time. Opening one shows its detail (M2-07).
///
/// One compact card: the status filter, then one row per activity (what it is, how it started, its CURRENT status) and the
/// counter of what is loaded. The only main action of the screen is the new activity.
class ActivitiesPage extends ConsumerWidget {
  const ActivitiesPage({super.key});

  String _originLabel(ActivityOrigin origin) =>
      origin == ActivityOrigin.planned ? 'Actividad planificada' : 'Actividad no planificada';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final filter = ref.watch(activityFilterProvider);
    final view = ref.watch(activityListProvider);
    final list = view.value;

    final filters = Wrap(
      spacing: AppSpace.sm,
      runSpacing: AppSpace.sm,
      children: [
        StatusChoice(
          key: const Key('activity-filter-all'),
          label: 'Todas',
          selected: filter.isEmpty,
          onTap: () => ref.read(activityFilterProvider.notifier).clear(),
        ),
        for (final status in ActivityStatus.values)
          StatusChoice(
            key: Key('activity-filter-${status.name}'),
            label: statusLabel(status),
            colors: statusColors(status),
            selected: filter.contains(status),
            onTap: () => ref.read(activityFilterProvider.notifier).toggle(status),
          ),
      ],
    );

    Widget body;
    if (view.isLoading) {
      body = const KeyedSubtree(key: Key('activities-loading'), child: LoadingBlock());
    } else if (view.hasError) {
      final error = view.error;
      body = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudieron cargar las actividades.',
        onRetry: () => ref.invalidate(activityListProvider),
      );
    } else if (list == null || list.items.isEmpty) {
      body = EmptyState(
        filter.isEmpty
            ? 'Todavía no tienes actividades. Planifica la primera desde Planificación.'
            : 'No hay actividades con este filtro.',
        key: const Key('activities-empty'),
      );
    } else {
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < list.items.length; i++)
            _ActivityRow(
              key: Key('activity-row-${list.items[i].id}'),
              activity: list.items[i],
              origin: _originLabel(list.items[i].origin),
              first: i == 0,
              onTap: () {
                ref.read(activityNavProvider.notifier).open(list.items[i].id, back: AppPage.activities);
                ref.read(currentPageProvider.notifier).go(AppPage.activityDetail);
              },
            ),
          if (list.hasMore || list.moreError != null) ...[
            const SizedBox(height: AppSpace.lg),
            if (list.moreError != null)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpace.md),
                child: FormErrorText(errorMessage(list.moreError!), textKey: const Key('activities-more-error'), center: true),
              ),
            Center(
              child: SecondaryButton(
                key: const Key('activities-load-more'),
                label: list.loadingMore
                    ? 'Cargando…'
                    : (list.moreError != null ? 'Reintentar' : 'Cargar más actividades'),
                onPressed: list.loadingMore ? null : () => ref.read(activityListProvider.notifier).loadMore(),
              ),
            ),
          ],
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Seguimiento de actividades',
          title: 'Mis actividades',
          subtitle: 'Todas tus actividades, sin importar la jornada en que las creaste.',
          action: PrimaryButton(
            key: const Key('activities-new-activity'),
            label: 'Nueva actividad',
            icon: Icons.add,
            onPressed: () => openNewActivity(context),
          ),
        ),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xxl),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const PanelHeader(
                      title: 'Lista de actividades',
                      subtitle: 'Filtra por el estado en que están hoy',
                      bottom: AppSpace.md,
                    ),
                    filters,
                    const SizedBox(height: AppSpace.md),
                    body,
                  ],
                ),
              ),
              PanelFooter(
                text: list == null
                    ? 'La lista se carga desde el servidor.'
                    : '${list.items.length} ${list.items.length == 1 ? 'actividad cargada' : 'actividades cargadas'}'
                          '${list.hasMore ? ' · hay más' : ''}',
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// One activity of the list: how it started, its title and its CURRENT status, all told in words. Selecting it opens its detail.
/// On a phone the status goes right after the title, so it is read with it.
class _ActivityRow extends StatelessWidget {
  const _ActivityRow({
    super.key,
    required this.activity,
    required this.origin,
    required this.first,
    required this.onTap,
  });

  final ActivitySummary activity;
  final String origin;
  final bool first;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final unplanned = activity.origin == ActivityOrigin.unplanned;
    final pill = KeyedSubtree(
      key: Key('row-status-${activity.id}'),
      child: StatusPill(label: statusLabel(activity.status), kind: pillKind(activity.status)),
    );
    return Semantics(
      button: true,
      label: '${activity.title}, ${statusLabel(activity.status)}',
      excludeSemantics: true,
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
        child: FocusRingInk(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpace.md, horizontal: AppSpace.xs),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: unplanned ? UnplannedColors.background : AppColors.progressBackground,
                    borderRadius: BorderRadius.circular(AppRadius.control),
                  ),
                  child: Icon(
                    activity.status == ActivityStatus.completed
                        ? Icons.check
                        : (unplanned ? Icons.bolt : Icons.event_note_outlined),
                    size: 18,
                    color: unplanned ? UnplannedColors.foreground : AppColors.progressText,
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        activity.title,
                        style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink),
                      ),
                      const SizedBox(height: AppSpace.xs),
                      Wrap(
                        spacing: AppSpace.sm,
                        runSpacing: AppSpace.xs,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          // How it started is told once: planned ones by this line, unplanned ones by their own tag
                          if (!unplanned) Text(origin, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
                          KeyedSubtree(key: Key('row-origin-${activity.id}'), child: OriginTag(origin: activity.origin)),
                          if (mobile) pill,
                        ],
                      ),
                    ],
                  ),
                ),
                if (!mobile) ...[const SizedBox(width: AppSpace.md), pill],
                const SizedBox(width: AppSpace.xs),
                const ExcludeSemantics(child: Icon(Icons.chevron_right, size: 20, color: AppColors.textSoft)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
