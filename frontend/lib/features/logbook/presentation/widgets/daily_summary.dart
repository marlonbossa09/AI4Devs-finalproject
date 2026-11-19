import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/kind_tag.dart';
import '../../../../core/widgets/toast.dart';
import '../../domain/entities/logbook_entities.dart';
import '../providers/logbook_notifier.dart';
import '../providers/unsaved_changes.dart';

/// The free-text summary of the day (M2-02), kept visibly apart from the activities and their
/// progress entries: it has its own block and its own tag.
///
/// - It shows what the server holds; after saving, the day is reloaded from the API.
/// - An empty summary is valid (it only prevents closing the day), so saving never requires text.
/// - A closed day cannot be edited: the server rejects it, so the screen does not offer it.
/// - A second tap while saving does nothing, and the field is disabled while the request runs.
class DailySummary extends ConsumerStatefulWidget {
  const DailySummary({super.key, required this.logbook});

  final Logbook logbook;

  @override
  ConsumerState<DailySummary> createState() => _DailySummaryState();
}

class _DailySummaryState extends ConsumerState<DailySummary> {
  final _controller = TextEditingController();
  bool _editing = false;
  bool _saving = false;
  String? _error;
  late final UnsavedGuard _guard = ref.read(unsavedGuardProvider);

  /// Text typed in the editor that the server does not hold yet. Opening the editor and typing
  /// nothing, or typing and then going back to the saved text, is not a change.
  bool _hasUnsaved() => _editing && !widget.logbook.closed && _controller.text != widget.logbook.summary;

  @override
  void initState() {
    super.initState();
    _guard.register(_hasUnsaved);
  }

  @override
  void dispose() {
    _guard.unregister(_hasUnsaved);
    _controller.dispose();
    super.dispose();
  }

  void _startEditing() {
    setState(() {
      _controller.text = widget.logbook.summary;
      _error = null;
      _editing = true;
    });
  }

  Future<void> _cancel() async {
    if (_saving) return;
    if (_hasUnsaved()) {
      final discard = await showConfirmDialog(
        context,
        title: 'Tienes cambios sin guardar',
        message: 'Si cierras el editor, el texto que escribiste en el resumen se perderá.',
        confirmLabel: 'Descartar cambios',
        cancelLabel: 'Seguir editando',
      );
      if (!discard || !mounted) return;
    }
    setState(() {
      _editing = false;
      _error = null;
    });
  }

  Future<void> _save() async {
    if (_saving) return; // a second tap while the request runs does nothing
    setState(() {
      _saving = true;
      _error = null;
    });
    // The user may change the date while the request runs, which unmounts this editor together with its own
    // subscriptions: the day notifier is held at CONTAINER level, so the answer is still applied and the day
    // reloaded.
    final provider = logbookProvider(widget.logbook.date);
    final keepAlive = ProviderScope.containerOf(context, listen: false).listen(provider, (previous, next) {});
    try {
      // The text goes exactly as typed: the server keeps it as received.
      await ref.read(provider.notifier).saveSummary(_controller.text);
      if (!mounted) return;
      setState(() {
        _saving = false;
        _editing = false;
      });
      showToast(context, 'Resumen guardado.');
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
    final logbook = widget.logbook;
    final closed = logbook.closed;
    final editing = _editing && !closed; // a day closed meanwhile leaves the editor
    final empty = logbook.summary.isEmpty;

    final tag = KindTag(
      'Resumen diario',
      icon: Icons.notes,
      color: AppColors.textLabel,
      background: const Color(0xFFEEF1F6),
    );
    final action = closed || editing
        ? null
        : LinkButton(
            key: const Key('summary-edit'),
            label: empty ? 'Escribir resumen' : 'Editar resumen',
            onPressed: _startEditing,
          );

    return Container(
      key: const Key('summary-section'),
      width: double.infinity,
      padding: EdgeInsets.all(mobile ? 14 : 16),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 6,
            children: [tag, ?action],
          ),
          const SizedBox(height: 8),
          const Text(
            'Texto libre sobre tu jornada. No es una actividad ni un avance.',
            style: TextStyle(fontSize: 12, color: AppColors.textSoft),
          ),
          const SizedBox(height: 12),
          if (editing) ...[
            LabeledField(
              fieldKey: const Key('summary-field'),
              label: 'Resumen de la jornada',
              hint: 'Cuenta cómo fue tu jornada con tus propias palabras',
              controller: _controller,
              enabled: !_saving,
              minLines: 4,
              maxLines: 12,
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Semantics(
                liveRegion: true,
                child: Text(
                  _error!,
                  key: const Key('summary-error'),
                  style: const TextStyle(fontSize: 12, color: AppColors.error),
                ),
              ),
            ],
            const SizedBox(height: 14),
            if (mobile)
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  PrimaryButton(
                    key: const Key('summary-save'),
                    label: 'Guardar resumen',
                    icon: Icons.check,
                    loading: _saving,
                    expand: true,
                    onPressed: _save,
                  ),
                  const SizedBox(height: 10),
                  SecondaryButton(key: const Key('summary-cancel'), label: 'Cancelar', onPressed: _saving ? null : _cancel),
                ],
              )
            else
              Wrap(
                alignment: WrapAlignment.end,
                spacing: 10,
                runSpacing: 8,
                children: [
                  SecondaryButton(key: const Key('summary-cancel'), label: 'Cancelar', onPressed: _saving ? null : _cancel),
                  PrimaryButton(
                    key: const Key('summary-save'),
                    label: 'Guardar resumen',
                    icon: Icons.check,
                    loading: _saving,
                    onPressed: _save,
                  ),
                ],
              ),
          ] else ...[
            Text(
              empty ? 'Sin resumen' : logbook.summary,
              key: Key(empty ? 'summary-empty' : 'summary-text'),
              style: TextStyle(
                fontSize: 12,
                height: 1.65,
                color: empty ? AppColors.textSoft : AppColors.textBody,
                fontStyle: empty ? FontStyle.italic : FontStyle.normal,
              ),
            ),
            if (closed) ...[
              const SizedBox(height: 12),
              const Row(
                key: Key('summary-closed-note'),
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: EdgeInsets.only(top: 1),
                    child: Icon(Icons.lock_outline, size: 13, color: AppColors.textFaint),
                  ),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'La jornada está cerrada. Para cambiar el resumen hay que reabrirla.',
                      style: TextStyle(fontSize: 12, height: 1.5, color: AppColors.textSoft),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ],
      ),
    );
  }
}
