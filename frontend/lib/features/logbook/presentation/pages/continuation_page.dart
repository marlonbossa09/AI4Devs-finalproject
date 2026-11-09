import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/utils/keys.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../../core/widgets/toast.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/continuation_rules.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../widgets/activity_tile.dart';
import '../widgets/continuation_tag.dart';
import '../widgets/origin_tag.dart';

/// Form to plan the continuation of an existing activity for a later day (M2-04).
///
/// - It is a PLANNING: it creates no progress entry, does not create another activity and does not
///   change the status. The activity keeps its identity.
/// - The date must be after today; the description is optional.
/// - The idempotency key identifies ONE intention: retrying the same request reuses it, changing
///   what is sent gets a new one, and the server accepting the request ends it.
class ContinuationPage extends ConsumerStatefulWidget {
  const ContinuationPage({super.key});

  @override
  ConsumerState<ContinuationPage> createState() => _ContinuationPageState();
}

class _ContinuationPageState extends ConsumerState<ContinuationPage> {
  final _description = TextEditingController();
  final _intention = IntentionKey();

  late final ContinuationTargetState? _target = ref.read(continuationTargetProvider);

  /// Where the user came from (Mi bitácora by default, or the activity detail).
  late final AppPage _back = _target?.back ?? AppPage.logbook;
  late DateTime _date = _startDate();
  bool _saving = false;
  ContinuationErrors _errors = const ContinuationErrors();
  String? _error;

  DateTime get _today => ref.read(authProvider).value?.today ?? dateOnly(DateTime.now().toUtc());
  DateTime get _tomorrow => _today.add(const Duration(days: 1));

  /// The day being looked at when it is already a future one; otherwise tomorrow.
  DateTime _startDate() {
    final selected = ref.read(selectedDateProvider);
    return selected.isAfter(_today) ? selected : _tomorrow;
  }

  @override
  void dispose() {
    _description.dispose();
    super.dispose();
  }

  Future<void> _submit(ActivitySummary activity) async {
    if (_saving) return; // a second tap while the request runs does nothing
    final errors = validateContinuation(date: _date, today: _today);
    if (!errors.isEmpty) {
      setState(() {
        _errors = errors;
        _error = null;
      });
      return;
    }
    final description = _description.text.trim();
    final key = _intention.forRequest([activity.id, formatDate(_date), description].join('|'));
    setState(() {
      _saving = true;
      _errors = const ContinuationErrors();
      _error = null;
    });
    final provider = logbookProvider(_date);
    // Keeps the notifier alive while the request runs, even if nothing else is watching it.
    final keepAlive = ref.listenManual(provider, (previous, next) {});
    try {
      await ref
          .read(provider.notifier)
          .planContinuation(
            activityId: activity.id,
            description: description.isEmpty ? null : description,
            key: key,
          );
      if (!mounted) return;
      _intention.accepted(); // the next continuation is a new intention
      _description.clear();
      setState(() => _saving = false);
      showToast(context, 'Continuación planificada.');
      ref.read(selectedDateProvider.notifier).select(_date);
      ref.read(currentPageProvider.notifier).go(_back);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = errorMessage(error);
      });
    } finally {
      keepAlive.close();
    }
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final activity = _target?.activity;

    final cancelButton = SecondaryButton(
      key: const Key('continuation-cancel'),
      label: 'Cancelar',
      onPressed: _saving ? null : () => ref.read(currentPageProvider.notifier).go(_back),
    );

    Widget form;
    if (activity == null) {
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const EmptyState('Elige una actividad para planificar su continuación.', key: Key('continuation-none')),
          Align(alignment: Alignment.centerLeft, child: cancelButton),
        ],
      );
    } else {
      final eligible = canPlanContinuation(status: activity.status, marked: false);
      final dateField = DateField(
        fieldKey: const Key('continuation-date'),
        label: 'Fecha de la continuación *',
        date: _date,
        firstDate: _tomorrow,
        errorText: _errors.date,
        onChanged: (value) => setState(() {
          _date = value;
          _errors = const ContinuationErrors();
        }),
      );
      final descriptionField = LabeledField(
        fieldKey: const Key('continuation-description'),
        label: 'Descripción',
        hint: '¿Qué tienes previsto hacer ese día?',
        controller: _description,
        enabled: !_saving,
        minLines: 4,
        maxLines: 6,
      );
      final saveButton = PrimaryButton(
        key: const Key('continuation-submit'),
        label: 'Planificar continuación',
        icon: Icons.event_repeat_outlined,
        loading: _saving,
        expand: mobile,
        onPressed: eligible ? () => _submit(activity) : null,
      );
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ActivityBox(activity: activity),
          const SizedBox(height: 14),
          if (!eligible) ...[
            const Notice(
              key: Key('continuation-completed-notice'),
              title: 'Actividad completada',
              text:
                  'Una actividad completada no admite continuaciones planificadas. Para continuarla '
                  'después habrá que reactivarla.',
              icon: Icons.info_outline,
            ),
            const SizedBox(height: 14),
          ],
          dateField,
          const SizedBox(height: 14),
          descriptionField,
          const SizedBox(height: 10),
          const Text(
            'Es una planificación: no registra ningún avance ni cambia el estado de la actividad.',
            key: Key('continuation-hint'),
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          if (_error != null) ...[
            const SizedBox(height: 14),
            Semantics(
              liveRegion: true,
              child: Text(
                _error!,
                key: const Key('continuation-error'),
                style: const TextStyle(fontSize: 12, color: AppColors.error),
              ),
            ),
          ],
          const SizedBox(height: 17),
          if (mobile)
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                saveButton,
                const SizedBox(height: 10),
                SizedBox(width: double.infinity, child: cancelButton),
              ],
            )
          else
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [cancelButton, const SizedBox(width: 10), saveButton],
            ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Seguimiento de actividades',
          title: 'Planificar continuación',
          subtitle: 'Deja prevista la continuación de una actividad para una jornada posterior.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 790),
            child: AppCard(
              padding: EdgeInsets.all(mobile ? 18 : 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Align(alignment: Alignment.centerLeft, child: ContinuationTag()),
                  const SizedBox(height: 10),
                  const PanelHeader(
                    title: 'Detalles de la continuación',
                    subtitle: 'La actividad es la misma: solo se añade lo previsto para otro día',
                  ),
                  form,
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// The activity being continued: it is shown, not chosen, so the user always knows which one it is.
class _ActivityBox extends StatelessWidget {
  const _ActivityBox({required this.activity});

  final ActivitySummary activity;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('continuation-activity'),
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: AppColors.border),
      ),
      child: Wrap(
        spacing: 10,
        runSpacing: 6,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          const Text('Actividad', style: TextStyle(fontSize: 10, color: AppColors.textFaint)),
          Text(activity.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
          OriginTag(origin: activity.origin),
          KeyedSubtree(
            key: const Key('continuation-activity-status'),
            child: StatusPill(label: statusLabel(activity.status), kind: pillKind(activity.status)),
          ),
        ],
      ),
    );
  }
}
