import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/keys.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../../core/widgets/toast.dart';
import '../providers/logbook_notifier.dart';
import '../providers/navigation.dart';
import '../providers/selected_date.dart';

/// Form to plan a new activity (M2-03).
///
/// The idempotency key identifies ONE intention: it is reused when retrying the same one (for
/// instance after a network error) and renewed only after the server accepts it.
class PlanningPage extends ConsumerStatefulWidget {
  const PlanningPage({super.key});

  @override
  ConsumerState<PlanningPage> createState() => _PlanningPageState();
}

class _PlanningPageState extends ConsumerState<PlanningPage> {
  final _title = TextEditingController();
  final _description = TextEditingController();
  late DateTime _date = ref.read(selectedDateProvider);
  String _key = newKey();
  bool _saving = false;
  String? _titleError;
  String? _error;

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    final title = _title.text.trim();
    if (title.isEmpty) {
      // The server also validates it; this only avoids a useless round trip.
      setState(() {
        _titleError = 'El título es obligatorio.';
        _error = null;
      });
      return;
    }
    setState(() {
      _saving = true;
      _titleError = null;
      _error = null;
    });
    final description = _description.text.trim();
    final provider = logbookProvider(_date);
    // Keeps the notifier alive while the request runs, even if nothing else is watching it.
    final keepAlive = ref.listenManual(provider, (previous, next) {});
    try {
      await ref
          .read(provider.notifier)
          .createActivity(
            title: title,
            description: description.isEmpty ? null : description,
            key: _key,
          );
      if (!mounted) return;
      _title.clear();
      _description.clear();
      _key = newKey(); // the next one is a new intention
      setState(() => _saving = false);
      showToast(context, 'Actividad planificada.');
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
      fieldKey: const Key('plan-title'),
      label: 'Título de la actividad *',
      hint: 'Ej. Revisar requerimientos del módulo',
      controller: _title,
      errorText: _titleError,
      textInputAction: TextInputAction.next,
    );
    final dateField = DateField(
      fieldKey: const Key('plan-date'),
      label: 'Fecha de planificación *',
      date: _date,
      onChanged: (value) => setState(() => _date = value),
    );
    const statusField = LabeledField(
      label: 'Estado inicial',
      hint: 'Pendiente',
      enabled: false,
      hintBelow: 'Una planificación nueva inicia como pendiente.',
    );
    final descriptionField = LabeledField(
      fieldKey: const Key('plan-description'),
      label: 'Descripción',
      hint: '¿Qué tienes previsto realizar?',
      controller: _description,
      minLines: 4,
      maxLines: 6,
    );

    final cancelButton = SecondaryButton(
      key: const Key('plan-cancel'),
      label: 'Cancelar',
      onPressed: () => ref.read(currentPageProvider.notifier).go(AppPage.dashboard),
    );
    final saveButton = PrimaryButton(
      key: const Key('plan-submit'),
      label: 'Guardar planificación',
      icon: Icons.add,
      loading: _saving,
      expand: mobile,
      onPressed: _save,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Organiza tu jornada',
          title: 'Nueva planificación',
          subtitle: 'Registra lo que tienes previsto hacer, sin alterar el estado de ejecución.',
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
                    subtitle: 'Completa la información de tu nueva planificación',
                  ),
                  titleField,
                  const SizedBox(height: 14),
                  if (mobile) ...[
                    dateField,
                    const SizedBox(height: 14),
                    statusField,
                  ] else
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: dateField),
                        const SizedBox(width: 14),
                        const Expanded(child: statusField),
                      ],
                    ),
                  const SizedBox(height: 14),
                  descriptionField,
                  if (_error != null) ...[
                    const SizedBox(height: 14),
                    Semantics(
                      liveRegion: true,
                      child: Text(
                        _error!,
                        key: const Key('plan-error'),
                        style: const TextStyle(fontSize: 12, color: AppColors.error),
                      ),
                    ),
                  ],
                  const SizedBox(height: 17),
                  if (mobile)
                    // Narrow screens: stacked and full width, the main action first.
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
