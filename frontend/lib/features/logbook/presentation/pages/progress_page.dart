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
import '../../../../core/widgets/text_blocks.dart';
import '../../../../core/widgets/toast.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/progress_rules.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../widgets/status_picker.dart';

/// Form to record a progress entry on one of the user's activities (M2-05).
///
/// - The activity is chosen among those of the day being looked at (the one the user came from).
/// - The work date cannot be in the future; a past date records a retroactive entry.
/// - The block reason only exists for the blocked status.
/// - The idempotency key identifies ONE intention: retrying the same request reuses it, changing
///   what is sent gets a new one, and the server accepting the request ends it.
class ProgressPage extends ConsumerStatefulWidget {
  const ProgressPage({super.key});

  @override
  ConsumerState<ProgressPage> createState() => _ProgressPageState();
}

class _ProgressPageState extends ConsumerState<ProgressPage> {
  final _description = TextEditingController();
  final _blockReason = TextEditingController();
  final _intention = IntentionKey();

  late final ProgressTargetState? _target = ref.read(progressTargetProvider);
  late String? _activityId = _target?.activity.id;

  /// Where the user came from (Mi bitácora by default, or the activity detail).
  late final AppPage _back = _target?.back ?? AppPage.logbook;
  late DateTime _date = _startDate();
  ActivityStatus? _status;
  bool _saving = false;
  ProgressErrors _errors = const ProgressErrors();
  String? _error;

  DateTime get _today => ref.read(authProvider).value?.today ?? dateOnly(DateTime.now().toUtc());

  /// The day being looked at, unless it is in the future: only what already happened is recorded.
  DateTime _startDate() {
    final selected = ref.read(selectedDateProvider);
    final today = _today;
    return selected.isAfter(today) ? today : selected;
  }

  @override
  void dispose() {
    _description.dispose();
    _blockReason.dispose();
    super.dispose();
  }

  /// The chosen activity, only if it is still among the ones offered.
  ActivitySummary? _chosen(List<ActivitySummary> offered) {
    for (final activity in offered) {
      if (activity.id == _activityId) return activity;
    }
    return null;
  }

  Future<void> _submit(List<ActivitySummary> offered) async {
    if (_saving) return; // a second tap while the request runs does nothing
    final activity = _chosen(offered);
    final errors = validateProgress(
      activityId: activity?.id,
      date: _date,
      today: _today,
      status: _status,
      description: _description.text,
      blockReason: _blockReason.text,
    );
    if (!errors.isEmpty) {
      setState(() {
        _errors = errors;
        _error = null;
      });
      return;
    }
    final status = _status!;
    final description = _description.text.trim();
    final blockReason = status == ActivityStatus.blocked ? _blockReason.text.trim() : null;
    final key = _intention.forRequest(
      [activity!.id, formatDate(_date), status.name, description, blockReason ?? ''].join('|'),
    );
    setState(() {
      _saving = true;
      _errors = const ProgressErrors();
      _error = null;
    });
    final provider = logbookProvider(_date);
    // Keeps the notifier alive while the request runs, even if nothing else is watching it.
    final keepAlive = ref.listenManual(provider, (previous, next) {});
    try {
      await ref
          .read(provider.notifier)
          .registerProgress(
            activityId: activity.id,
            status: status,
            description: description,
            blockReason: blockReason,
            key: key,
          );
      if (!mounted) return;
      _intention.accepted(); // the next entry is a new intention
      _description.clear();
      _blockReason.clear();
      setState(() {
        _saving = false;
        _status = null;
      });
      showToast(context, 'Avance registrado.');
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
    final listedDate = ref.watch(selectedDateProvider);
    final view = ref.watch(logbookProvider(listedDate));
    // The activities of the day being looked at, plus the one chosen from the list or the detail
    // (which may belong to another day)
    final offered = <ActivitySummary>[
      for (final a in view.value?.activities ?? const <Activity>[])
        if (!a.marked) a.summary,
    ];
    final target = _target?.activity;
    if (target != null && offered.every((a) => a.id != target.id)) offered.insert(0, target);
    final chosen = _chosen(offered);

    final activityField = SelectField<String>(
      key: const Key('progress-activity'),
      label: 'Actividad *',
      hint: offered.isEmpty ? 'No hay actividades para elegir' : 'Elige una actividad',
      options: {for (final a in offered) a.id: a.title},
      value: chosen?.id,
      errorText: _errors.activity,
      enabled: !_saving && offered.isNotEmpty,
      onChanged: (id) => setState(() {
        _activityId = id;
        _errors = const ProgressErrors();
      }),
    );
    final dateField = DateField(
      fieldKey: const Key('progress-date'),
      label: 'Fecha laboral *',
      date: _date,
      lastDate: _today,
      errorText: _errors.date,
      onChanged: (value) => setState(() {
        _date = value;
        _errors = const ProgressErrors();
      }),
    );
    final statusPicker = StatusPicker(
      selected: _status,
      enabled: !_saving,
      errorText: _errors.status,
      onChanged: (value) => setState(() {
        _status = value;
        if (value != ActivityStatus.blocked) _blockReason.clear(); // the reason only exists when blocked
        _errors = const ProgressErrors();
      }),
    );
    final reasonField = LabeledField(
      fieldKey: const Key('progress-reason'),
      label: 'Motivo del bloqueo *',
      hint: '¿Qué impide avanzar?',
      controller: _blockReason,
      enabled: !_saving,
      minLines: 2,
      maxLines: 4,
      errorText: _errors.blockReason,
    );
    final descriptionField = LabeledField(
      fieldKey: const Key('progress-description'),
      label: 'Descripción del avance *',
      hint: '¿Qué hiciste en esta jornada?',
      controller: _description,
      enabled: !_saving,
      minLines: 4,
      maxLines: 6,
      errorText: _errors.description,
    );

    final cancelButton = SecondaryButton(
      key: const Key('progress-cancel'),
      label: 'Cancelar',
      onPressed: _saving ? null : () => ref.read(currentPageProvider.notifier).go(_back),
    );
    final saveButton = PrimaryButton(
      key: const Key('progress-submit'),
      label: 'Registrar avance',
      icon: Icons.check,
      loading: _saving,
      expand: mobile,
      onPressed: () => _submit(offered),
    );

    Widget form;
    if (view.hasError && view.value == null) {
      final error = view.error;
      form = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudieron cargar las actividades.',
        onRetry: () => ref.invalidate(logbookProvider(listedDate)),
      );
    } else if (view.isLoading && view.value == null) {
      form = const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    } else {
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (mobile) ...[
            activityField,
            const SizedBox(height: 14),
            dateField,
          ] else
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 3, child: activityField),
                const SizedBox(width: 14),
                Expanded(flex: 2, child: dateField),
              ],
            ),
          if (offered.isEmpty) ...[
            const SizedBox(height: 10),
            Text(
              'Para registrar un avance, planifica una actividad o cambia la fecha en Mi bitácora (${formatShortDate(listedDate)}).',
              key: const Key('progress-no-activities'),
              style: const TextStyle(fontSize: 11, color: AppColors.textSoft),
            ),
          ],
          if (chosen?.status == ActivityStatus.completed) ...[
            const SizedBox(height: 14),
            const Notice(
              key: Key('progress-completed-notice'),
              title: 'Actividad completada',
              text:
                  'Solo se admiten avances con fecha anterior a su finalización. Para continuarla después '
                  'habrá que reactivarla.',
              icon: Icons.info_outline,
            ),
          ],
          const SizedBox(height: 14),
          statusPicker,
          if (_status == ActivityStatus.blocked) ...[const SizedBox(height: 14), reasonField],
          const SizedBox(height: 14),
          descriptionField,
          if (_error != null) ...[
            const SizedBox(height: 14),
            Semantics(
              liveRegion: true,
              child: Text(
                _error!,
                key: const Key('progress-error'),
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
          title: 'Registrar avance',
          subtitle: 'Deja constancia de lo realizado y del estado en que queda la actividad.',
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
                  PanelHeader(
                    title: 'Detalles del avance',
                    subtitle: 'Actividades de la jornada ${formatShortDate(listedDate)}',
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
