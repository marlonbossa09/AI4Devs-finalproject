import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../widgets/activity_tile.dart';
import '../widgets/logbook_summary.dart';

/// The logbook of the selected date, exactly as persisted on the server.
class LogbookPage extends ConsumerStatefulWidget {
  const LogbookPage({super.key});

  @override
  ConsumerState<LogbookPage> createState() => _LogbookPageState();
}

class _LogbookPageState extends ConsumerState<LogbookPage> {
  bool _opening = false;
  String? _openError;

  void _registerProgress(Activity activity) {
    ref.read(progressTargetProvider.notifier).select(activity.summary);
    ref.read(currentPageProvider.notifier).go(AppPage.progress);
  }

  void _openDetail(Activity activity) {
    ref.read(activityNavProvider.notifier).open(activity.id, back: AppPage.logbook);
    ref.read(currentPageProvider.notifier).go(AppPage.activityDetail);
  }

  Future<void> _open(DateTime date) async {
    setState(() {
      _opening = true;
      _openError = null;
    });
    try {
      await ref.read(logbookProvider(date).notifier).open();
      if (mounted) setState(() => _opening = false);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _opening = false;
        _openError = errorMessage(error);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final date = ref.watch(selectedDateProvider);
    final view = ref.watch(logbookProvider(date));
    final day = view.value;

    final dateField = SizedBox(
      width: mobile ? double.infinity : 210,
      child: DateField(
        fieldKey: const Key('work-date'),
        label: 'Fecha laboral',
        date: date,
        onChanged: (value) {
          setState(() => _openError = null);
          ref.read(selectedDateProvider.notifier).select(value);
        },
      ),
    );

    Widget body;
    if (view.hasError && day == null) {
      final error = view.error;
      body = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la bitácora.',
        onRetry: () => ref.invalidate(logbookProvider(date)),
      );
    } else if (view.isLoading && day == null) {
      body = const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (day == null) {
      body = _NoLogbook(
        opening: _opening,
        error: _openError,
        onOpen: () => _open(date),
      );
    } else {
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LogbookSummary(logbook: day.logbook),
          const SizedBox(height: 18),
          if (day.activities.isEmpty)
            const EmptyState('No hay actividades para esta selección.')
          else
            for (var i = 0; i < day.activities.length; i++)
              ActivityTile(
                key: Key('activity-${day.activities[i].id}'),
                activity: day.activities[i],
                planning: day.planningOf(day.activities[i]),
                progress: day.progressOf(day.activities[i]),
                onRegisterProgress: () => _registerProgress(day.activities[i]),
                onOpen: () => _openDetail(day.activities[i]),
                first: i == 0,
              ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Registro personal',
          title: 'Mi bitácora',
          subtitle: 'Consulta y organiza tus actividades por fecha laboral.',
          action: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              SecondaryButton(
                key: const Key('logbook-new-unplanned'),
                label: 'Actividad no planificada',
                onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.unplanned),
              ),
              PrimaryButton(
                key: const Key('logbook-new-planning'),
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
                    PanelHeader(
                      title: 'Jornada de trabajo',
                      subtitle: 'Lo que está guardado en el servidor para esta fecha',
                      trailing: mobile ? null : dateField,
                    ),
                    if (mobile) ...[dateField, const SizedBox(height: 18)],
                    body,
                  ],
                ),
              ),
              PanelFooter(
                text: 'La planificación es distinta de un avance de ejecución.',
                action: LinkButton(
                  label: 'Nueva planificación →',
                  onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.planning),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _NoLogbook extends StatelessWidget {
  const _NoLogbook({required this.opening, required this.error, required this.onOpen});

  final bool opening;
  final String? error;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 20),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE8EDF3)),
      ),
      child: Column(
        children: [
          const Text(
            'No hay bitácora para esta fecha.',
            key: Key('no-logbook'),
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          const Text(
            'Puedes abrirla ahora, o se creará al planificar una actividad.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: Color(0xFF8292A2)),
          ),
          if (error != null) ...[
            const SizedBox(height: 10),
            Text(
              error!,
              key: const Key('open-error'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: Color(0xFFBD5954)),
            ),
          ],
          const SizedBox(height: 16),
          SecondaryButton(
            key: const Key('open-logbook'),
            label: 'Abrir bitácora',
            onPressed: opening ? null : onOpen,
          ),
        ],
      ),
    );
  }
}
