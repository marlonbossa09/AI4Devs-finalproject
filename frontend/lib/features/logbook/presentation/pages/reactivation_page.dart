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
import '../../domain/rules/reactivation_rules.dart';
import '../providers/activity_detail.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';
import '../widgets/activity_tile.dart';
import '../widgets/closed_date_notice.dart';
import '../widgets/origin_tag.dart';
import '../widgets/reactivation_tag.dart';
import '../widgets/status_picker.dart';

/// Form to reactivate a Completada activity (M3-04).
///
/// - A reactivation is a progress entry of the SAME activity that comes after its completion: it does not
///   create another activity and does not rewrite or remove anything that was recorded.
/// - The work date cannot be before the completion (the same day is valid) nor in the future.
/// - It leaves the activity Pendiente, En progreso or Bloqueada (with a reason); never Completada.
/// - The idempotency key identifies ONE intention: retrying the same request reuses it, changing what is
///   sent gets a new one, and the server accepting the request ends it.
class ReactivationPage extends ConsumerStatefulWidget {
  const ReactivationPage({super.key});

  @override
  ConsumerState<ReactivationPage> createState() => _ReactivationPageState();
}

class _ReactivationPageState extends ConsumerState<ReactivationPage> {
  final _description = TextEditingController();
  final _blockReason = TextEditingController();
  final _intention = IntentionKey();

  late final ReactivationTargetState? _target = ref.read(reactivationTargetProvider);

  /// Where the user came from (Mi bitácora by default, or the activity detail).
  late final AppPage _back = _target?.back ?? AppPage.logbook;
  late DateTime _date = _today;
  ActivityStatus? _status;
  bool _saving = false;
  ReactivationErrors _errors = const ReactivationErrors();
  String? _error;

  DateTime get _today => ref.read(authProvider).value?.today ?? dateOnly(DateTime.now().toUtc());

  @override
  void dispose() {
    _description.dispose();
    _blockReason.dispose();
    super.dispose();
  }

  /// The work date of the completion that determines the current status: the last entry of the sequence.
  DateTime? _completedOn(ActivityDetail? detail) =>
      detail == null || detail.progress.isEmpty ? null : detail.progress.last.date;

  Future<void> _submit(ActivitySummary activity, DateTime? completedOn) async {
    if (_saving) return; // a second tap while the request runs does nothing
    final errors = validateReactivation(
      date: _date,
      today: _today,
      completedOn: completedOn,
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
    final key = _intention.forRequest([activity.id, formatDate(_date), status.name, description, blockReason ?? ''].join('|'));
    setState(() {
      _saving = true;
      _errors = const ReactivationErrors();
      _error = null;
    });
    final provider = logbookProvider(_date);
    // Keeps the notifier alive while the request runs, even if nothing else is watching it.
    final keepAlive = ref.listenManual(provider, (previous, next) {});
    try {
      await ref
          .read(provider.notifier)
          .reactivate(
            activityId: activity.id,
            status: status,
            description: description,
            blockReason: blockReason,
            key: key,
          );
      if (!mounted) return;
      _intention.accepted(); // the next reactivation is a new intention
      _description.clear();
      _blockReason.clear();
      setState(() {
        _saving = false;
        _status = null;
      });
      showToast(context, 'Actividad reactivada.');
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
    final detailView = activity == null ? null : ref.watch(activityDetailProvider(activity.id));
    final detail = detailView?.value;
    final completedOn = _completedOn(detail);
    final closedDate = ref.watch(logbookProvider(_date)).value?.logbook.closed ?? false;

    final cancelButton = SecondaryButton(
      key: const Key('reactivation-cancel'),
      label: 'Cancelar',
      onPressed: _saving ? null : () => ref.read(currentPageProvider.notifier).go(_back),
    );

    Widget form;
    if (activity == null) {
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const EmptyState('Elige una actividad completada para reactivarla.', key: Key('reactivation-none')),
          Align(alignment: Alignment.centerLeft, child: cancelButton),
        ],
      );
    } else if (detailView != null && detailView.isLoading && detail == null) {
      form = const Padding(
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    } else if (detailView != null && detailView.hasError && detail == null) {
      final error = detailView.error;
      form = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
        onRetry: () => ref.invalidate(activityDetailProvider(activity.id)),
      );
    } else {
      // While the request runs the detail is reloaded; the form stays as it is until it finishes
      final status = detail?.status ?? activity.status;
      final eligible = _saving || canReactivate(status: status, marked: detail?.activity.marked ?? false);
      final dateField = DateField(
        fieldKey: const Key('reactivation-date'),
        label: 'Fecha laboral *',
        date: _date,
        firstDate: completedOn,
        lastDate: _today,
        errorText: _errors.date,
        onChanged: (value) => setState(() {
          _date = value;
          _errors = const ReactivationErrors();
        }),
      );
      final statusPicker = StatusPicker(
        keyPrefix: 'reactivation-status',
        statuses: reactivationStatuses,
        selected: _status,
        enabled: !_saving,
        errorText: _errors.status,
        onChanged: (value) => setState(() {
          _status = value;
          if (value != ActivityStatus.blocked) _blockReason.clear(); // the reason only exists when blocked
          _errors = const ReactivationErrors();
        }),
      );
      final reasonField = LabeledField(
        fieldKey: const Key('reactivation-reason'),
        label: 'Motivo del bloqueo *',
        hint: '¿Qué impide avanzar?',
        controller: _blockReason,
        enabled: !_saving,
        minLines: 2,
        maxLines: 4,
        errorText: _errors.blockReason,
      );
      final descriptionField = LabeledField(
        fieldKey: const Key('reactivation-description'),
        label: 'Descripción de la reactivación *',
        hint: '¿Por qué o cómo retomas la actividad?',
        controller: _description,
        enabled: !_saving,
        minLines: 4,
        maxLines: 6,
        errorText: _errors.description,
      );
      final saveButton = PrimaryButton(
        key: const Key('reactivation-submit'),
        label: 'Reactivar actividad',
        icon: Icons.replay,
        loading: _saving,
        expand: mobile,
        onPressed: eligible && !closedDate ? () => _submit(activity, completedOn) : null,
      );
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ActivityBox(activity: activity, status: status, completedOn: completedOn),
          const SizedBox(height: 14),
          if (!eligible) ...[
            const Notice(
              key: Key('reactivation-not-completed'),
              title: 'La actividad ya no está completada',
              text: 'Solo se reactiva una actividad Completada. Vuelve atrás para ver su estado actual.',
              icon: Icons.info_outline,
            ),
            const SizedBox(height: 14),
          ],
          dateField,
          const SizedBox(height: 14),
          statusPicker,
          if (_status == ActivityStatus.blocked) ...[const SizedBox(height: 14), reasonField],
          const SizedBox(height: 14),
          descriptionField,
          const SizedBox(height: 10),
          const Text(
            'Es una ejecución nueva de la misma actividad: queda después de su finalización y no borra ni modifica nada de lo ya registrado.',
            key: Key('reactivation-hint'),
            style: TextStyle(fontSize: 11, color: AppColors.textSoft),
          ),
          if (closedDate) ...[const SizedBox(height: 14), ClosedDateNotice(date: _date)],
          if (_error != null) ...[
            const SizedBox(height: 14),
            Semantics(
              liveRegion: true,
              child: Text(
                _error!,
                key: const Key('reactivation-error'),
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
          title: 'Reactivar actividad',
          subtitle: 'Retoma una actividad completada sin crear otra: queda como la misma, con su historial.',
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
                  const Align(alignment: Alignment.centerLeft, child: ReactivationTag()),
                  const SizedBox(height: 10),
                  const PanelHeader(
                    title: 'Detalles de la reactivación',
                    subtitle: 'Se añade al historial como un avance de reactivación',
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

/// The activity being reactivated and when it was completed: it is shown, not chosen.
class _ActivityBox extends StatelessWidget {
  const _ActivityBox({required this.activity, required this.status, required this.completedOn});

  final ActivitySummary activity;
  final ActivityStatus status;
  final DateTime? completedOn;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('reactivation-activity'),
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              const Text('Actividad', style: TextStyle(fontSize: 10, color: AppColors.textFaint)),
              Text(activity.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
              OriginTag(origin: activity.origin),
              KeyedSubtree(
                key: const Key('reactivation-activity-status'),
                child: StatusPill(label: statusLabel(status), kind: pillKind(status)),
              ),
            ],
          ),
          if (completedOn != null) ...[
            const SizedBox(height: 6),
            Text(
              'Completada el ${formatShortDate(completedOn!)}. La reactivación puede tener esa misma fecha o una posterior.',
              key: const Key('reactivation-completed-on'),
              style: const TextStyle(fontSize: 11, color: AppColors.textSoft),
            ),
          ],
        ],
      ),
    );
  }
}
