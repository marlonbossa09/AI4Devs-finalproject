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
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/focus_ring.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../../core/widgets/toast.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/progress_rules.dart';
import '../providers/logbook_notifier.dart';
import '../providers/selected_date.dart';
import '../providers/side_panel.dart';
import '../providers/unsaved_changes.dart';
import 'closed_date_notice.dart';
import 'status_picker.dart';

/// The two things the panel can create. They are DIFFERENT operations with different contracts, so they are two forms, each with its
/// own fields and rules, never one form with switches:
/// - [planned] (M2-03): a title, a work date and an optional description. It creates the activity as Pendiente with its original
///   planning; it registers no progress.
/// - [unplanned] (M2-06): a title, a work date that is not in the future, a status, a description and, only for Bloqueada, a reason.
///   It creates the activity AND its first progress entry in one operation.
enum NewActivityKind { planned, unplanned }

/// Opens the "Nueva actividad" side panel over the screen the person is on. Nothing navigates: when it is saved the panel closes and the
/// person is still where they were.
void openNewActivity(BuildContext context, {NewActivityKind kind = NewActivityKind.planned}) {
  final container = ProviderScope.containerOf(context);
  final messenger = ScaffoldMessenger.of(context);
  // The confirmation of a previous save sits where the panel's action strip is: it is dismissed so it never covers the new save button
  messenger.hideCurrentSnackBar();
  final controller = NewActivityController(
    container: container,
    messenger: messenger,
    screenWidth: MediaQuery.sizeOf(context).width,
    kind: kind,
  );
  container.read(sidePanelProvider.notifier).open(
    SidePanelRequest(
      title: 'Nueva actividad',
      subtitle: 'Registra una actividad en tu jornada.',
      icon: Icons.add,
      bodyBuilder: (context) => NewActivityBody(controller: controller),
      actionsBuilder: (context) => NewActivityActions(controller: controller),
      isBusy: () => controller.saving,
      hasUnsaved: controller.hasUnsaved,
    ),
  );
}

/// State of the panel, shared by its body and its action strip (they are separate parts of the side panel).
///
/// - **One request per intention.** The idempotency key identifies ONE intention in both forms: retrying the same content reuses it,
///   changing what is sent gets a new one, and the server accepting it ends it. While a request runs a second one is ignored.
/// - **Nothing is lost on a recoverable error.** The panel stays open with everything the person typed, and says what happened.
/// - **Unsaved text** is reported to the app's single `UnsavedGuard`, so closing, Escape, a tap outside, changing page, signing out
///   and opening another panel all ask the same question.
class NewActivityController extends ChangeNotifier {
  NewActivityController({
    required this.container,
    required this.messenger,
    required this.screenWidth,
    required this.kind,
  }) {
    final selected = container.read(selectedDateProvider);
    plannedDate = selected;
    // Only what already happened is recorded as unplanned work
    unplannedDate = selected.isAfter(today) ? today : selected;
    // A field's error goes away as soon as the person fixes that field
    planTitle.addListener(_clearFixedErrors);
    title.addListener(_clearFixedErrors);
    description.addListener(_clearFixedErrors);
    blockReason.addListener(_clearFixedErrors);
  }

  void _clearFixedErrors() {
    var changed = false;
    if (planTitleError != null && planTitle.text.trim().isNotEmpty) {
      planTitleError = null;
      changed = true;
    }
    final current = errors;
    if (!current.isEmpty) {
      final next = ProgressErrors(
        title: title.text.trim().isEmpty ? current.title : null,
        date: current.date,
        status: current.status,
        description: description.text.trim().isEmpty ? current.description : null,
        blockReason: blockReason.text.trim().isEmpty ? current.blockReason : null,
      );
      if (next.title != current.title || next.description != current.description || next.blockReason != current.blockReason) {
        errors = next;
        changed = true;
      }
    }
    if (changed) _notify();
  }

  final ProviderContainer container;
  final ScaffoldMessengerState messenger;
  final double screenWidth;

  NewActivityKind kind;
  bool _saving = false;
  bool _disposed = false;

  // planned (M2-03)
  final planTitle = TextEditingController();
  final planDescription = TextEditingController();
  final planTitleFocus = FocusNode(debugLabel: 'plan-title');
  late DateTime plannedDate;
  final _planIntention = IntentionKey();
  String? planTitleError;

  // unplanned (M2-06)
  final title = TextEditingController();
  final description = TextEditingController();
  final blockReason = TextEditingController();
  final titleFocus = FocusNode(debugLabel: 'unplanned-title');
  late DateTime unplannedDate;
  ActivityStatus? status;
  final _intention = IntentionKey();
  ProgressErrors errors = const ProgressErrors();

  /// Problem of the last send, in the app's fixed words; null when there is none.
  String? error;

  bool get saving => _saving;

  DateTime get today => container.read(authProvider).value?.today ?? dateOnly(DateTime.now().toUtc());

  DateTime get date => kind == NewActivityKind.planned ? plannedDate : unplannedDate;

  /// Whether any field holds text that was typed and not saved.
  bool hasUnsaved() =>
      planTitle.text.trim().isNotEmpty ||
      planDescription.text.trim().isNotEmpty ||
      title.text.trim().isNotEmpty ||
      description.text.trim().isNotEmpty ||
      blockReason.text.trim().isNotEmpty;

  /// Called by the body when it is shown: starts reporting unsaved text.
  void attach() => container.read(unsavedGuardProvider).register(hasUnsaved);

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void setKind(NewActivityKind value) {
    if (_saving || value == kind) return;
    kind = value;
    error = null;
    _notify();
  }

  void setPlannedDate(DateTime value) {
    plannedDate = value;
    error = null;
    _notify();
  }

  void setUnplannedDate(DateTime value) {
    unplannedDate = value;
    errors = const ProgressErrors();
    error = null;
    _notify();
  }

  void setStatus(ActivityStatus value) {
    status = value;
    if (value != ActivityStatus.blocked) blockReason.clear(); // the reason only exists when blocked
    errors = const ProgressErrors();
    _notify();
  }

  /// Closes the panel the way every user-started close does (it may ask before discarding typed text).
  void cancel() => container.read(sidePanelProvider.notifier).requestClose();

  Future<void> submit() => kind == NewActivityKind.planned ? _submitPlanned() : _submitUnplanned();

  Future<void> _submitPlanned() async {
    if (_saving) return; // a second tap while the request runs does nothing
    final title = planTitle.text.trim();
    if (title.isEmpty) {
      // The server also validates it; this only avoids a useless round trip.
      planTitleError = 'El título es obligatorio.';
      error = null;
      _notify();
      return;
    }
    final description = planDescription.text.trim();
    final date = plannedDate;
    final key = _planIntention.forRequest([formatDate(date), title, description].join('|'));
    _saving = true;
    planTitleError = null;
    error = null;
    _notify();
    final provider = logbookProvider(date);
    // Keeps the notifier alive while the request runs, even if nothing else is watching it.
    final keepAlive = container.listen(provider, (previous, next) {});
    try {
      await container.read(provider.notifier).createActivity(title: title, description: description.isEmpty ? null : description, key: key);
      _planIntention.accepted(); // the next one is a new intention
      planTitle.clear();
      planDescription.clear();
      _saving = false;
      _finish('Actividad planificada', date, forDate: 'para el');
    } on ApiError catch (failure) {
      _saving = false;
      error = errorMessage(failure);
      _notify();
    } finally {
      keepAlive.close();
    }
  }

  Future<void> _submitUnplanned() async {
    if (_saving) return;
    final problems = validateUnplanned(
      title: title.text,
      date: unplannedDate,
      today: today,
      status: status,
      description: description.text,
      blockReason: blockReason.text,
    );
    if (!problems.isEmpty) {
      errors = problems;
      error = null;
      _notify();
      return;
    }
    final chosen = status!;
    final cleanTitle = title.text.trim();
    final cleanDescription = description.text.trim();
    final reason = chosen == ActivityStatus.blocked ? blockReason.text.trim() : null;
    final date = unplannedDate;
    final key = _intention.forRequest([formatDate(date), cleanTitle, chosen.name, cleanDescription, reason ?? ''].join('|'));
    _saving = true;
    errors = const ProgressErrors();
    error = null;
    _notify();
    final provider = logbookProvider(date);
    final keepAlive = container.listen(provider, (previous, next) {});
    try {
      await container
          .read(provider.notifier)
          .registerUnplanned(title: cleanTitle, status: chosen, description: cleanDescription, blockReason: reason, key: key);
      _intention.accepted(); // the next one is a new intention
      title.clear();
      description.clear();
      blockReason.clear();
      status = null;
      _saving = false;
      _finish('Actividad no planificada registrada', date, forDate: 'el');
    } on ApiError catch (failure) {
      _saving = false;
      error = errorMessage(failure);
      _notify();
    } finally {
      keepAlive.close();
    }
  }

  /// The server accepted it: the panel closes (the person stays on the screen they were on) and a short confirmation says what was
  /// saved. If it was saved for a date other than the one on screen, the confirmation names that date, so it is never mistaken for
  /// something that belongs to the day being looked at.
  void _finish(String message, DateTime saved, {required String forDate}) {
    container.read(sidePanelProvider.notifier).closeNow();
    final shown = container.read(selectedDateProvider);
    final text = saved == shown ? '$message.' : '$message $forDate ${formatShortDate(saved)}.';
    showToastOn(messenger, screenWidth, text);
  }

  @override
  void dispose() {
    _disposed = true;
    container.read(unsavedGuardProvider).unregister(hasUnsaved);
    for (final c in [planTitle, planDescription, title, description, blockReason]) {
      c.dispose();
    }
    planTitleFocus.dispose();
    titleFocus.dispose();
    super.dispose();
  }
}

/// Body of the panel: the date of the day, the choice of type and the form of the chosen type.
class NewActivityBody extends StatefulWidget {
  const NewActivityBody({super.key, required this.controller});

  final NewActivityController controller;

  @override
  State<NewActivityBody> createState() => _NewActivityBodyState();
}

class _NewActivityBodyState extends State<NewActivityBody> {
  NewActivityController get c => widget.controller;

  @override
  void initState() {
    super.initState();
    c.attach();
    // The first field of the form takes the focus when the panel opens (the panel itself already announced its name)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) (c.kind == NewActivityKind.planned ? c.planTitleFocus : c.titleFocus).requestFocus();
    });
  }

  @override
  void dispose() {
    c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: c,
      builder: (context, _) => Consumer(
        builder: (context, ref, _) {
          final closed = ref.watch(logbookProvider(c.date)).value?.logbook.closed ?? false;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _DateBanner(date: c.date),
              const SizedBox(height: AppSpace.lg),
              const FieldLabel('Tipo de actividad'),
              Row(
                children: [
                  Expanded(
                    child: _TypeChoice(
                      key: const Key('new-activity-type-planned'),
                      title: 'Planificada',
                      subtitle: 'Lo que tienes previsto realizar',
                      icon: Icons.event_note_outlined,
                      selected: c.kind == NewActivityKind.planned,
                      onTap: c.saving ? null : () => c.setKind(NewActivityKind.planned),
                    ),
                  ),
                  const SizedBox(width: AppSpace.md),
                  Expanded(
                    child: _TypeChoice(
                      key: const Key('new-activity-type-unplanned'),
                      title: 'No planificada',
                      subtitle: 'Surgió durante el trabajo',
                      icon: Icons.bolt,
                      selected: c.kind == NewActivityKind.unplanned,
                      onTap: c.saving ? null : () => c.setKind(NewActivityKind.unplanned),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpace.lg),
              if (c.kind == NewActivityKind.planned) _plannedForm(closed) else _unplannedForm(closed),
            ],
          );
        },
      ),
    );
  }

  Widget _plannedForm(bool closed) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LabeledField(
          fieldKey: const Key('plan-title'),
          focusNode: c.planTitleFocus,
          label: 'Título de la actividad *',
          hint: 'Ej. Revisar requerimientos del módulo',
          controller: c.planTitle,
          enabled: !c.saving,
          errorText: c.planTitleError,
          textInputAction: TextInputAction.next,
        ),
        const SizedBox(height: AppSpace.lg),
        DateField(
          fieldKey: const Key('plan-date'),
          label: 'Fecha laboral *',
          date: c.plannedDate,
          onChanged: c.saving ? (_) {} : c.setPlannedDate,
        ),
        const SizedBox(height: AppSpace.lg),
        const Notice(
          key: Key('plan-notice'),
          title: 'Estado inicial: Pendiente',
          text: 'Guardar una planificación no registra avances.',
          icon: Icons.info_outline,
        ),
        const SizedBox(height: AppSpace.lg),
        LabeledField(
          fieldKey: const Key('plan-description'),
          label: 'Descripción (opcional)',
          hint: '¿Qué tienes previsto realizar?',
          controller: c.planDescription,
          enabled: !c.saving,
          minLines: 3,
          maxLines: 5,
        ),
        if (closed) ...[const SizedBox(height: AppSpace.lg), ClosedDateNotice(date: c.plannedDate)],
        if (c.error != null) ...[const SizedBox(height: AppSpace.lg), _ErrorText(c.error!, const Key('plan-error'))],
      ],
    );
  }

  Widget _unplannedForm(bool closed) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Notice(
          key: Key('unplanned-notice'),
          title: 'Sin planificación previa',
          text: 'La actividad empezará en el estado que elijas aquí, que es el de su primer avance. No se crea ninguna planificación.',
          icon: Icons.info_outline,
        ),
        const SizedBox(height: AppSpace.lg),
        LabeledField(
          fieldKey: const Key('unplanned-title'),
          focusNode: c.titleFocus,
          label: 'Título de la actividad *',
          hint: 'Ej. Atender un incidente urgente',
          controller: c.title,
          enabled: !c.saving,
          errorText: c.errors.title,
          textInputAction: TextInputAction.next,
        ),
        const SizedBox(height: AppSpace.lg),
        DateField(
          fieldKey: const Key('unplanned-date'),
          label: 'Fecha laboral *',
          date: c.unplannedDate,
          lastDate: c.today,
          errorText: c.errors.date,
          onChanged: c.saving ? (_) {} : c.setUnplannedDate,
        ),
        const SizedBox(height: AppSpace.lg),
        StatusPicker(
          keyPrefix: 'unplanned-status',
          selected: c.status,
          enabled: !c.saving,
          errorText: c.errors.status,
          onChanged: c.setStatus,
        ),
        if (c.status == ActivityStatus.blocked) ...[
          const SizedBox(height: AppSpace.lg),
          LabeledField(
            fieldKey: const Key('unplanned-reason'),
            label: 'Motivo del bloqueo *',
            hint: '¿Qué impide avanzar?',
            controller: c.blockReason,
            enabled: !c.saving,
            minLines: 2,
            maxLines: 4,
            errorText: c.errors.blockReason,
          ),
        ],
        const SizedBox(height: AppSpace.lg),
        LabeledField(
          fieldKey: const Key('unplanned-description'),
          label: 'Descripción de lo realizado *',
          hint: '¿Qué hiciste?',
          controller: c.description,
          enabled: !c.saving,
          minLines: 3,
          maxLines: 5,
          errorText: c.errors.description,
        ),
        if (closed) ...[const SizedBox(height: AppSpace.lg), ClosedDateNotice(date: c.unplannedDate)],
        if (c.error != null) ...[const SizedBox(height: AppSpace.lg), _ErrorText(c.error!, const Key('unplanned-error'))],
      ],
    );
  }
}

/// Cancel and save, pinned under the body. While a request runs both are inert and the save button shows a spinner (no percentage).
class NewActivityActions extends StatelessWidget {
  const NewActivityActions({super.key, required this.controller});

  final NewActivityController controller;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) => Consumer(
        builder: (context, ref, _) {
          final planned = controller.kind == NewActivityKind.planned;
          // A closed day takes no new content: the chosen date is looked up and, if closed, nothing is offered
          final closed = ref.watch(logbookProvider(controller.date)).value?.logbook.closed ?? false;
          final cancel = SecondaryButton(
            key: Key(planned ? 'plan-cancel' : 'unplanned-cancel'),
            label: 'Cancelar',
            onPressed: controller.saving ? null : controller.cancel,
          );
          final save = PrimaryButton(
            key: Key(planned ? 'plan-submit' : 'unplanned-submit'),
            label: planned ? 'Guardar planificación' : 'Registrar actividad',
            icon: planned ? Icons.add : Icons.check,
            loading: controller.saving,
            onPressed: closed ? null : controller.submit,
          );
          if (mobile) {
            return Row(children: [Expanded(child: cancel), const SizedBox(width: AppSpace.md), Expanded(flex: 2, child: SizedBox(width: double.infinity, child: save))]);
          }
          // A Wrap, not a Row: with a larger text size the two buttons go on two lines instead of overflowing
          return Wrap(alignment: WrapAlignment.end, spacing: AppSpace.md, runSpacing: AppSpace.sm, children: [cancel, save]);
        },
      ),
    );
  }
}

/// "Fecha laboral: miércoles, 18 de noviembre de 2026": the day the activity is being created for.
class _DateBanner extends StatelessWidget {
  const _DateBanner({required this.date});

  final DateTime date;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('new-activity-date'),
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.md, vertical: AppSpace.sm + 2),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppRadius.control),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.calendar_today_outlined, size: 16, color: AppColors.muted),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text.rich(
              TextSpan(
                children: [
                  const TextSpan(text: 'Fecha laboral: ', style: TextStyle(color: AppColors.muted)),
                  TextSpan(text: formatTopDate(date), style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.ink)),
                ],
              ),
              style: const TextStyle(fontSize: AppType.body),
            ),
          ),
        ],
      ),
    );
  }
}

/// One of the two kinds. It is announced as a button of an exclusive group with its selected state; the selected one is also told by
/// a check, a thicker border and its background, not by color alone.
class _TypeChoice extends StatelessWidget {
  const _TypeChoice({super.key, required this.title, required this.subtitle, required this.icon, required this.selected, required this.onTap});

  final String title;
  final String subtitle;
  final IconData icon;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      inMutuallyExclusiveGroup: true,
      enabled: onTap != null,
      label: '$title. $subtitle',
      excludeSemantics: true,
      onTap: onTap,
      child: Material(
        color: selected ? AppColors.primarySoft : AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: selected ? AppColors.primary : AppColors.fieldBorder, width: selected ? 2 : 1),
          ),
          child: FocusRingInk(
            borderRadius: BorderRadius.circular(AppRadius.card),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 72),
              child: Padding(
                padding: const EdgeInsets.all(AppSpace.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(icon, size: 16, color: selected ? AppColors.primary : AppColors.muted),
                        const SizedBox(width: AppSpace.xs + 2),
                        Expanded(child: Text(title, style: const TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w800, color: AppColors.ink))),
                        if (selected) const Icon(Icons.check_circle, size: 18, color: AppColors.primary),
                      ],
                    ),
                    const SizedBox(height: AppSpace.xs),
                    Text(subtitle, style: const TextStyle(fontSize: AppType.caption, color: AppColors.muted)),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorText extends StatelessWidget {
  const _ErrorText(this.text, this.textKey);

  final String text;
  final Key textKey;

  @override
  Widget build(BuildContext context) => Semantics(
    liveRegion: true,
    child: Text(text, key: textKey, style: const TextStyle(fontSize: AppType.caption, color: AppColors.error)),
  );
}
