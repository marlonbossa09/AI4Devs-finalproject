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

/// Form to register work that was NOT planned (M2-06): one operation that creates the activity,
/// flagged as unplanned, and its first progress entry.
///
/// - The activity starts with the status of that first entry (RN-69); no planning is invented.
/// - The work date cannot be in the future; a past date registers a past day.
/// - The block reason only exists for the blocked status.
/// - The idempotency key identifies ONE intention: retrying the same request reuses it, changing what
///   is sent gets a new one, and the server accepting the request ends it.
class UnplannedPage extends ConsumerStatefulWidget {
  const UnplannedPage({super.key});

  @override
  ConsumerState<UnplannedPage> createState() => _UnplannedPageState();
}

class _UnplannedPageState extends ConsumerState<UnplannedPage> {
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _blockReason = TextEditingController();
  final _intention = IntentionKey();

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
    _title.dispose();
    _description.dispose();
    _blockReason.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_saving) return; // a second tap while the request runs does nothing
    final errors = validateUnplanned(
      title: _title.text,
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
    final title = _title.text.trim();
    final description = _description.text.trim();
    final blockReason = status == ActivityStatus.blocked ? _blockReason.text.trim() : null;
    final key = _intention.forRequest(
      [formatDate(_date), title, status.name, description, blockReason ?? ''].join('|'),
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
          .registerUnplanned(title: title, status: status, description: description, blockReason: blockReason, key: key);
      if (!mounted) return;
      _intention.accepted(); // the next one is a new intention
      _title.clear();
      _description.clear();
      _blockReason.clear();
      setState(() {
        _saving = false;
        _status = null;
      });
      showToast(context, 'Actividad no planificada registrada.');
      ref.read(selectedDateProvider.notifier).select(_date);
      ref.read(currentPageProvider.notifier).go(AppPage.logbook);
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
    final titleField = LabeledField(
      fieldKey: const Key('unplanned-title'),
      label: 'Título de la actividad *',
      hint: 'Ej. Atender un incidente urgente',
      controller: _title,
      enabled: !_saving,
      errorText: _errors.title,
      textInputAction: TextInputAction.next,
    );
    final dateField = DateField(
      fieldKey: const Key('unplanned-date'),
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
      keyPrefix: 'unplanned-status',
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
      fieldKey: const Key('unplanned-reason'),
      label: 'Motivo del bloqueo *',
      hint: '¿Qué impide avanzar?',
      controller: _blockReason,
      enabled: !_saving,
      minLines: 2,
      maxLines: 4,
      errorText: _errors.blockReason,
    );
    final descriptionField = LabeledField(
      fieldKey: const Key('unplanned-description'),
      label: 'Descripción de lo realizado *',
      hint: '¿Qué hiciste?',
      controller: _description,
      enabled: !_saving,
      minLines: 4,
      maxLines: 6,
      errorText: _errors.description,
    );

    final cancelButton = SecondaryButton(
      key: const Key('unplanned-cancel'),
      label: 'Cancelar',
      onPressed: _saving ? null : () => ref.read(currentPageProvider.notifier).go(AppPage.dashboard),
    );
    final saveButton = PrimaryButton(
      key: const Key('unplanned-submit'),
      label: 'Registrar actividad',
      icon: Icons.check,
      loading: _saving,
      expand: mobile,
      onPressed: _submit,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Seguimiento de actividades',
          title: 'Actividad no planificada',
          subtitle: 'Registra trabajo que surgió sin haberlo planificado antes.',
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
                  const PanelHeader(
                    title: 'Detalles de la actividad',
                    subtitle: 'Se registrará como no planificada, con su primer avance',
                  ),
                  const Notice(
                    key: Key('unplanned-notice'),
                    title: 'Sin planificación previa',
                    text:
                        'La actividad empezará en el estado que elijas aquí, que es el de su primer avance. '
                        'No se crea ninguna planificación.',
                    icon: Icons.info_outline,
                  ),
                  const SizedBox(height: 16),
                  titleField,
                  const SizedBox(height: 14),
                  dateField,
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
                        key: const Key('unplanned-error'),
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
              ),
            ),
          ),
        ),
      ],
    );
  }
}
