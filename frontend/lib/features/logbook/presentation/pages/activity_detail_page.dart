import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/activity_detail.dart';
import '../providers/navigation.dart';
import '../widgets/activity_tile.dart';
import '../widgets/origin_tag.dart';

/// One activity with everything recorded about it (M2-07). What was PLANNED and what was DONE are
/// shown in separate blocks, so a planning is never mistaken for a progress entry (CA-40).
class ActivityDetailPage extends ConsumerWidget {
  const ActivityDetailPage({super.key});

  String _backLabel(AppPage page) => switch (page) {
    AppPage.logbook => 'Mi bitácora',
    AppPage.dashboard => 'Panel principal',
    _ => 'Mis actividades',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final opened = ref.watch(activityNavProvider);
    if (opened == null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const EmptyState('No hay una actividad abierta.', key: Key('detail-none')),
          LinkButton(
            key: const Key('detail-back'),
            label: '← Mis actividades',
            onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.activities),
          ),
        ],
      );
    }
    final view = ref.watch(activityDetailProvider(opened.id));

    Widget body;
    if (view.isLoading) {
      body = const Padding(
        key: Key('detail-loading'),
        padding: EdgeInsets.all(40),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (view.hasError) {
      final error = view.error;
      body = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
        onRetry: () => ref.invalidate(activityDetailProvider(opened.id)),
      );
    } else {
      body = _DetailBody(
        detail: view.requireValue,
        onRegisterProgress: () {
          final activity = view.requireValue.activity;
          ref.read(progressTargetProvider.notifier).select(activity.summary, back: AppPage.activityDetail);
          ref.read(currentPageProvider.notifier).go(AppPage.progress);
        },
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: LinkButton(
            key: const Key('detail-back'),
            label: '← ${_backLabel(opened.back)}',
            onPressed: () => ref.read(currentPageProvider.notifier).go(opened.back),
          ),
        ),
        body,
      ],
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({required this.detail, required this.onRegisterProgress});

  final ActivityDetail detail;
  final VoidCallback onRegisterProgress;

  @override
  Widget build(BuildContext context) {
    final activity = detail.activity;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        PageHeader(
          eyebrow: 'Detalle de actividad',
          title: activity.title,
          subtitle: 'Lo que se planificó, lo que se hizo y el estado en que está hoy.',
          action: PrimaryButton(
            key: const Key('detail-register-progress'),
            label: 'Registrar avance',
            icon: Icons.add,
            onPressed: activity.marked ? null : onRegisterProgress,
          ),
        ),
        _StatusCard(detail: detail),
        const SizedBox(height: 18),
        _PlanningCard(detail: detail),
        const SizedBox(height: 18),
        _HistoryCard(progress: detail.progress),
      ],
    );
  }
}

/// A small uppercase tag that says which kind of record a block holds.
class _KindTag extends StatelessWidget {
  const _KindTag(this.text, {required this.icon, required this.color, required this.background});

  final String text;
  final IconData icon;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(color: background, borderRadius: BorderRadius.circular(7)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 5),
          Text(
            text.toUpperCase(),
            style: TextStyle(fontSize: 9.5, letterSpacing: 1.1, fontWeight: FontWeight.w800, color: color),
          ),
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.detail});

  final ActivityDetail detail;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final activity = detail.activity;
    final origin = activity.origin == ActivityOrigin.planned ? 'Actividad planificada' : 'Actividad no planificada';
    Widget fact(String label, String value, {Key? key}) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textFaint)),
        const SizedBox(height: 3),
        Text(value, key: key, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
      ],
    );
    return AppCard(
      padding: EdgeInsets.all(mobile ? 18 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('Estado actual', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
              const SizedBox(width: 12),
              KeyedSubtree(
                key: const Key('detail-status'),
                child: StatusPill(label: statusLabel(detail.status), kind: pillKind(detail.status)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'El del último avance de ejecución; Pendiente si todavía no tiene ninguno.',
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 34,
            runSpacing: 12,
            children: [
              if (activity.origin == ActivityOrigin.unplanned)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Tipo', style: TextStyle(fontSize: 10, color: AppColors.textFaint)),
                    const SizedBox(height: 3),
                    KeyedSubtree(key: const Key('detail-origin-tag'), child: OriginTag(origin: activity.origin)),
                  ],
                )
              else
                fact('Tipo', origin),
              fact('Jornada de origen', formatShortDate(activity.date), key: const Key('detail-origin-date')),
              fact('Creada el', formatDateTime(activity.createdAt)),
            ],
          ),
          if (activity.marked) ...[
            const SizedBox(height: 16),
            Container(
              key: const Key('detail-marked'),
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.blockedBackground,
                borderRadius: BorderRadius.circular(11),
              ),
              child: Text(
                'Esta actividad se marcó como registrada por error y ya no admite avances. '
                'Su historial se conserva.'
                '${activity.markReason == null || activity.markReason!.isEmpty ? '' : ' Motivo: ${activity.markReason}'}',
                style: const TextStyle(fontSize: 11, height: 1.6, color: AppColors.blockedText),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// WHAT WAS FORESEEN. Not a progress entry: it never changes the status.
class _PlanningCard extends StatelessWidget {
  const _PlanningCard({required this.detail});

  final ActivityDetail detail;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final original = detail.originalPlanning;

    Widget block(Key key, String title, String date, String description, {String? registered}) {
      return Container(
        key: key,
        width: double.infinity,
        margin: const EdgeInsets.only(top: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: const Color(0xFFF3FAF8),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: const Color(0xFFDAEEE9)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 10,
              children: [
                Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF276A67))),
                Text(date, style: const TextStyle(fontSize: 11, color: Color(0xFF276A67))),
                if (registered != null)
                  Text('Registrada $registered', style: const TextStyle(fontSize: 10, color: AppColors.textFaint)),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              description.isEmpty ? 'Sin descripción' : description,
              style: const TextStyle(fontSize: 12, height: 1.6, color: AppColors.textBody),
            ),
          ],
        ),
      );
    }

    return AppCard(
      padding: EdgeInsets.all(mobile ? 18 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _KindTag('Planificación', icon: Icons.event_note_outlined, color: Color(0xFF276A67), background: Color(0xFFE5F7F3)),
          const SizedBox(height: 10),
          const Text('Lo planificado', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text(
            'Lo que se tenía previsto. No es un avance y no cambia el estado de la actividad.',
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          if (original != null)
            block(
              const Key('detail-planning-original'),
              'Planificación original',
              formatShortDate(original.date),
              original.description,
              registered: formatDateTime(original.createdAt),
            )
          else
            Container(
              key: const Key('detail-no-planning'),
              margin: const EdgeInsets.only(top: 10),
              child: const Text(
                'Esta actividad no se planificó: se registró directamente como ejecución.',
                style: TextStyle(fontSize: 12, color: AppColors.textSoft),
              ),
            ),
          for (final next in detail.plannedContinuations)
            block(
              Key('detail-planning-${next.id}'),
              'Continuación prevista',
              formatShortDate(next.date),
              next.description,
              registered: formatDateTime(next.createdAt),
            ),
        ],
      ),
    );
  }
}

/// WHAT WAS DONE. Each entry keeps the status the activity had when it was recorded.
class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.progress});

  final List<Progress> progress;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    return AppCard(
      padding: EdgeInsets.all(mobile ? 18 : 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _KindTag('Ejecución', icon: Icons.trending_up, color: AppColors.progressText, background: AppColors.progressBackground),
          const SizedBox(height: 10),
          const Text('Historial de avances', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text(
            'Lo que realmente se hizo, ordenado por fecha laboral. Cada avance conserva el estado que tenía entonces.',
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          const SizedBox(height: 8),
          if (progress.isEmpty)
            const EmptyState('Todavía no hay avances registrados.', key: Key('detail-no-progress'))
          else
            for (var i = 0; i < progress.length; i++)
              _ProgressEntry(key: Key('detail-progress-${progress[i].id}'), entry: progress[i], first: i == 0),
        ],
      ),
    );
  }
}

class _ProgressEntry extends StatelessWidget {
  const _ProgressEntry({super.key, required this.entry, required this.first});

  final Progress entry;
  final bool first;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final reason = entry.blockReason;
    final date = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Fecha laboral', style: TextStyle(fontSize: 10, color: AppColors.textFaint)),
        const SizedBox(height: 2),
        Text(
          formatShortDate(entry.date),
          key: Key('detail-progress-date-${entry.id}'),
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 4),
        Text(
          'Registrado ${formatDateTime(entry.createdAt)}',
          style: const TextStyle(fontSize: 10, color: AppColors.textFaint),
        ),
      ],
    );
    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            KeyedSubtree(
              key: Key('detail-progress-status-${entry.id}'),
              child: StatusPill(label: statusLabel(entry.status), kind: pillKind(entry.status)),
            ),
            if (entry.isReactivation)
              const Text('Reactivación', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.textSoft)),
          ],
        ),
        const SizedBox(height: 8),
        Text(entry.description, style: const TextStyle(fontSize: 12, height: 1.6, color: AppColors.textBody)),
        if (reason != null && reason.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(
            'Motivo del bloqueo: $reason',
            style: const TextStyle(fontSize: 11, height: 1.55, color: AppColors.blockedText),
          ),
        ],
      ],
    );
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 15),
      decoration: BoxDecoration(
        border: first ? null : const Border(top: BorderSide(color: AppColors.divider)),
      ),
      child: mobile
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [date, const SizedBox(height: 10), content],
            )
          : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [SizedBox(width: 150, child: date), const SizedBox(width: 18), Expanded(child: content)],
            ),
    );
  }
}
