import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/utils/keys.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/status_pill.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../../core/widgets/toast.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/correction_rules.dart';
import '../providers/activity_detail.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../widgets/activity_tile.dart';
import '../widgets/closed_date_notice.dart';
import '../widgets/form_parts.dart';
import '../widgets/marked_tag.dart';
import '../widgets/reactivation_tag.dart';
import '../widgets/status_picker.dart';

/// Form to correct a progress entry already recorded (M3-03).
///
/// - It is a CORRECTION, not a new entry: the entry keeps its identifier, its work date, the moment it was
///   recorded and whether it is a reactivation. Only its status, its description and its block reason can change,
///   and the previous values stay in the audit.
/// - The work date is shown, never edited.
/// - The server validates the whole sequence of the activity; this form explains the same rule before sending,
///   and shows the server rejection if it still happens.
/// - Correcting what changes the current status of the activity asks for a confirmation first.
/// - The idempotency key identifies ONE intention: retrying the same correction reuses it, changing what is sent
///   gets a new one, and the server accepting it ends it.
class CorrectionPage extends ConsumerStatefulWidget {
  const CorrectionPage({super.key});

  @override
  ConsumerState<CorrectionPage> createState() => _CorrectionPageState();
}

class _CorrectionPageState extends ConsumerState<CorrectionPage> {
  final _description = TextEditingController();
  final _blockReason = TextEditingController();
  final _intention = IntentionKey();

  late final CorrectionTargetState? _target = ref.read(correctionTargetProvider);
  late final AppPage _back = _target?.back ?? AppPage.activityDetail;

  /// The form starts as the entry is; it is filled once, when the entry first arrives, and never again (a reload
  /// while the request runs must not overwrite what the user typed).
  bool _filled = false;
  ActivityStatus? _status;
  bool _saving = false;
  CorrectionErrors _errors = const CorrectionErrors();
  String? _error;

  @override
  void dispose() {
    _description.dispose();
    _blockReason.dispose();
    super.dispose();
  }

  void _fill(Progress entry) {
    if (_filled) return;
    _filled = true;
    _status = entry.status;
    _description.text = entry.description;
    _blockReason.text = entry.blockReason ?? '';
  }

  void _clearErrors() => setState(() {
    _errors = const CorrectionErrors();
    _error = null;
  });

  Future<void> _submit(ActivityDetail detail, Progress entry) async {
    if (_saving) return; // a second tap while the request runs does nothing
    final status = _status ?? entry.status;
    final errors = validateCorrection(
      original: entry,
      progress: detail.progress,
      status: status,
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
    final correction = buildCorrection(
      original: entry,
      status: status,
      description: _description.text,
      blockReason: _blockReason.text,
    );
    // Changing the current status of the activity is a bigger effect than rewording: it is confirmed first
    final before = detail.status;
    final after = currentStatusAfter(detail.progress, entry.id, status);
    if (after != before) {
      final confirmed = await showConfirmDialog(
        context,
        title: 'Esta corrección cambia el estado actual',
        message:
            'La actividad pasará de ${statusLabel(before)} a ${statusLabel(after)}. Queda constancia del valor '
            'anterior en la auditoría y puedes volver a corregirlo.',
        confirmLabel: 'Corregir avance',
        cancelLabel: 'Volver',
        destructive: false,
        icon: Icons.edit_outlined,
      );
      if (!confirmed || !mounted) return;
    }
    final key = _intention.forRequest([
      entry.id,
      correction.status?.name ?? '',
      correction.description ?? '',
      correction.blockReason ?? '',
    ].join('|'));
    setState(() {
      _saving = true;
      _errors = const CorrectionErrors();
      _error = null;
    });
    final provider = logbookProvider(entry.date);
    // Keeps the notifier alive while the request runs, even if nothing else is watching it.
    final keepAlive = ref.listenManual(provider, (previous, next) {});
    try {
      await ref.read(provider.notifier).correctProgress(progressId: entry.id, correction: correction, key: key);
      if (!mounted) return;
      _intention.accepted(); // the next correction is a new intention
      setState(() => _saving = false);
      showToast(context, 'Avance corregido.');
      ref.read(currentPageProvider.notifier).go(_back);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = _messageOf(error);
      });
    } finally {
      keepAlive.close();
    }
  }

  /// A rejection of the sequence says which rule it breaks; the rest use the common messages.
  String _messageOf(ApiError error) {
    if (error.code == 'SECUENCIA_INVALIDA') {
      final reason = error.details.isEmpty ? null : error.details.first['motivo'];
      final problem = switch (reason) {
        'avance_tras_finalizacion_sin_reactivacion' => SequenceProblem.progressAfterCompletion,
        'reactivacion_sin_finalizacion' => SequenceProblem.reactivationWithoutCompletion,
        'reactivacion_con_estado_completada' => SequenceProblem.reactivationCompleted,
        _ => null,
      };
      return problem == null
          ? 'La corrección dejaría la secuencia de avances de la actividad sin sentido. No se ha cambiado nada.'
          : '${sequenceProblemMessage(problem)} No se ha cambiado nada.';
    }
    return errorMessage(error);
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final target = _target;
    final detailView = target == null ? null : ref.watch(activityDetailProvider(target.activityId));
    final detail = detailView?.value;
    Progress? entry;
    if (detail != null) {
      for (final candidate in detail.progress) {
        if (candidate.id == target!.progressId) entry = candidate;
      }
    }
    if (entry != null) _fill(entry);
    final closedDay = entry == null ? false : (ref.watch(logbookProvider(entry.date)).value?.logbook.closed ?? false);

    final cancelButton = SecondaryButton(
      key: const Key('correction-cancel'),
      label: 'Cancelar',
      onPressed: _saving ? null : () => ref.read(currentPageProvider.notifier).go(_back),
    );

    Widget form;
    Widget? actions;
    if (target == null) {
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const EmptyState('Elige un avance de una actividad para corregirlo.', key: Key('correction-none')),
          Align(alignment: Alignment.centerLeft, child: cancelButton),
        ],
      );
    } else if (detailView != null && detailView.isLoading && detail == null) {
      form = const LoadingBlock();
    } else if (detailView != null && detailView.hasError && detail == null) {
      final error = detailView.error;
      form = ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la actividad.',
        onRetry: () => ref.invalidate(activityDetailProvider(target.activityId)),
      );
    } else if (detail == null || entry == null) {
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const EmptyState('Ese avance ya no está disponible.', key: Key('correction-gone')),
          Align(alignment: Alignment.centerLeft, child: cancelButton),
        ],
      );
    } else {
      final original = entry;
      final marked = detail.activity.marked;
      final blocked = !canCorrect(detail.activity);
      final status = _status ?? original.status;
      final submitEnabled = !blocked && !closedDay;
      final statusPicker = StatusPicker(
        keyPrefix: 'correction-status',
        label: 'Estado del avance *',
        statuses: correctionStatuses(original),
        selected: status,
        enabled: !_saving && submitEnabled,
        errorText: _errors.sequence,
        onChanged: (value) => setState(() {
          _status = value;
          _errors = const CorrectionErrors();
          _error = null;
        }),
      );
      final reasonField = LabeledField(
        fieldKey: const Key('correction-reason'),
        label: 'Motivo del bloqueo *',
        hint: '¿Qué impide avanzar?',
        controller: _blockReason,
        enabled: !_saving && submitEnabled,
        minLines: 2,
        maxLines: 4,
        errorText: _errors.blockReason,
        onChanged: (_) => _clearErrors(),
      );
      final descriptionField = LabeledField(
        fieldKey: const Key('correction-description'),
        label: 'Descripción *',
        hint: 'Lo que se hizo',
        controller: _description,
        enabled: !_saving && submitEnabled,
        minLines: 3,
        maxLines: 6,
        errorText: _errors.description,
        onChanged: (_) => _clearErrors(),
      );
      final saveButton = PrimaryButton(
        key: const Key('correction-submit'),
        label: 'Guardar corrección',
        icon: Icons.edit_outlined,
        loading: _saving,
        expand: mobile,
        onPressed: submitEnabled ? () => _submit(detail, original) : null,
      );
      actions = FormActions(cancel: cancelButton, submit: saveButton);
      const gap = SizedBox(height: AppSpace.lg);
      form = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _EntryBox(activity: detail.activity, entry: original),
          gap,
          if (marked) ...[
            const Notice(
              key: Key('correction-marked'),
              title: 'La actividad está marcada como registrada por error',
              text: 'Sus avances no se corrigen mientras la marca esté vigente. Revierte la marca desde el detalle de la actividad.',
              icon: Icons.report_gmailerrorred_outlined,
            ),
            gap,
          ],
          if (closedDay && !marked) ...[_ClosedDayNotice(date: original.date), gap],
          statusPicker,
          if (status == ActivityStatus.blocked) ...[gap, reasonField],
          gap,
          descriptionField,
          const SizedBox(height: AppSpace.md),
          const FormHint(
            'Es una corrección: no crea un avance nuevo, no cambia su fecha laboral ni borra nada. '
            'Queda constancia del valor anterior.',
            textKey: Key('correction-hint'),
          ),
          if (_errors.nothingChanged) ...[
            gap,
            const FormErrorText(
              'No has cambiado nada: modifica el estado, la descripción o el motivo para corregir el avance.',
              textKey: Key('correction-nothing'),
            ),
          ],
          if (_error != null) ...[gap, FormErrorText(_error!, textKey: const Key('correction-error'))],
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Seguimiento de actividades',
          title: 'Corregir avance',
          subtitle: 'Corrige lo que se registró en un avance, sin crear otro y dejando constancia.',
        ),
        FormColumn(
          child: FormCard(
            title: 'Datos del avance',
            subtitle: 'La fecha laboral y el momento de registro no se pueden cambiar',
            actions: actions,
            child: form,
          ),
        ),
      ],
    );
  }
}

/// The entry being corrected, as it is now: shown, never chosen. The work date is read-only.
class _EntryBox extends StatelessWidget {
  const _EntryBox({required this.activity, required this.entry});

  final Activity activity;
  final Progress entry;

  @override
  Widget build(BuildContext context) {
    return ContextBox(
      key: const Key('correction-entry'),
      title: activity.title,
      badges: [
        if (activity.marked) const MarkedTag(),
        KeyedSubtree(
          key: const Key('correction-entry-status'),
          child: StatusPill(label: statusLabel(entry.status), kind: pillKind(entry.status)),
        ),
        if (entry.isReactivation) const KeyedSubtree(key: Key('correction-reactivation-tag'), child: ReactivationTag()),
      ],
      details: [
        Text(
          'Fecha laboral: ${formatShortDate(entry.date)}',
          key: const Key('correction-date'),
          style: const TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w800, color: AppColors.ink),
        ),
        ContextFact('Registrado ${formatDateTime(entry.createdAt)}'),
        if (entry.corrected)
          Text(
            'Última corrección ${formatDateTime(entry.modifiedAt!)}',
            key: const Key('correction-last'),
            style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
          ),
      ],
    );
  }
}

/// The logbook of the entry's day is closed: it has to be reopened first (CA-284). The day cannot be changed here
/// because the work date of an entry is not corrected.
class _ClosedDayNotice extends StatelessWidget {
  const _ClosedDayNotice({required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    return ClosedDayBox(
      boxKey: const Key('correction-closed-notice'),
      text:
          'La jornada del ${formatShortDate(date)} está cerrada, así que este avance no se puede corregir. '
          'Reábrela desde Mi bitácora indicando un motivo y vuelve a intentarlo.',
    );
  }
}
