import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/activity_list.dart';
import '../providers/navigation.dart';
import '../widgets/activity_tile.dart';
import '../widgets/origin_tag.dart';
import '../widgets/status_choice.dart';

/// All the user's activities (M2-08), newest first, filtered by current status and loaded one page
/// at a time. Opening one shows its detail (M2-07).
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
      spacing: 8,
      runSpacing: 8,
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
      body = const Padding(
        key: Key('activities-loading'),
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
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
            const SizedBox(height: 16),
            if (list.moreError != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(
                  errorMessage(list.moreError!),
                  key: const Key('activities-more-error'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: AppColors.error),
                ),
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
          action: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              SecondaryButton(
                key: const Key('activities-new-unplanned'),
                label: 'Actividad no planificada',
                onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.unplanned),
              ),
              PrimaryButton(
                key: const Key('activities-new-planning'),
                label: 'Planificar actividad',
                icon: Icons.add,
                onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.planning),
              ),
            ],
          ),
        ),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: EdgeInsets.all(mobile ? 18 : 24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const PanelHeader(
                      title: 'Lista de actividades',
                      subtitle: 'Filtra por el estado en que están hoy',
                    ),
                    filters,
                    const SizedBox(height: 14),
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
    return Semantics(
      button: true,
      label: '${activity.title}, ${statusLabel(activity.status)}',
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 15),
          decoration: BoxDecoration(
            border: first ? null : const Border(top: BorderSide(color: AppColors.divider)),
          ),
          child: Row(
            children: [
              Container(
                width: 37,
                height: 37,
                decoration: BoxDecoration(
                  color: activity.origin == ActivityOrigin.unplanned ? UnplannedColors.background : const Color(0xFFE7F2FA),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: Icon(
                  activity.status == ActivityStatus.completed
                      ? Icons.check
                      : (activity.origin == ActivityOrigin.unplanned ? Icons.bolt : Icons.event_note_outlined),
                  size: 18,
                  color: activity.origin == ActivityOrigin.unplanned ? UnplannedColors.foreground : const Color(0xFF4C829D),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(activity.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(origin, style: const TextStyle(fontSize: 11, color: AppColors.textSoft)),
                        KeyedSubtree(key: Key('row-origin-${activity.id}'), child: OriginTag(origin: activity.origin)),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              KeyedSubtree(
                key: Key('row-status-${activity.id}'),
                child: StatusPill(label: statusLabel(activity.status), kind: pillKind(activity.status)),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.chevron_right, size: 18, color: AppColors.textFaint),
            ],
          ),
        ),
      ),
    );
  }
}
