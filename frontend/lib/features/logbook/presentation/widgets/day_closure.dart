import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/utils/keys.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/toast.dart';
import '../../domain/entities/logbook_entities.dart';
import '../../domain/rules/closing_rules.dart';
import '../providers/logbook_notifier.dart';
import '../providers/unsaved_changes.dart';
import 'reopen_dialog.dart';

/// Closing and reopening of the day (M3-01, M3-02), kept apart from the activities and the summary.
///
/// - An OPEN day shows what closing needs (a summary with text and an activity created or continued in
///   it) and the action to close it, always after a confirmation. If something is missing, the screen says
///   what, in plain sentences, and sends nothing.
/// - A CLOSED day is visibly different: it says when it was closed and offers to reopen it, with a
///   mandatory reason.
/// - A FUTURE day is not closed (CA-97): the screen only says so.
/// - Both actions show loading, ignore a second tap while they run, and use one idempotency key per
///   intention (reused when retrying, renewed once the server accepts it).
class DayClosure extends ConsumerStatefulWidget {
  const DayClosure({super.key, required this.day});

  final LogbookDay day;

  @override
  ConsumerState<DayClosure> createState() => _DayClosureState();
}

class _DayClosureState extends ConsumerState<DayClosure> {
  final _closeIntention = IntentionKey();
  final _reopenIntention = IntentionKey();
  bool _busy = false;
  List<String> _missing = const [];
  String? _error;

  Logbook get _logbook => widget.day.logbook;

  /// Unsaved summary text is asked about first (the guard), because closing judges what is SAVED.
  void _close() => ref.read(leaveRequestProvider.notifier).request(_confirmAndClose);

  Future<void> _confirmAndClose() async {
    if (_busy || !mounted) return;
    final conditions = closingConditions(widget.day);
    if (!conditions.met) {
      setState(() {
        _missing = conditions.missing;
        _error = null;
      });
      return;
    }
    final confirmed = await showConfirmDialog(
      context,
      title: '¿Cerrar la jornada?',
      message:
          'Una vez cerrada, su resumen y sus actividades no se modifican sin reabrirla. Tus actividades '
          'conservan su estado y quedará constancia del cierre.',
      confirmLabel: 'Cerrar jornada',
      cancelLabel: 'Todavía no',
      destructive: false,
      icon: Icons.lock_outline,
    );
    if (!confirmed || !mounted) return;
    setState(() {
      _busy = true;
      _missing = const [];
      _error = null;
    });
    // The user may change the date while the request runs. That unmounts this widget, and a widget's own
    // subscriptions die with it, so the day notifier is held by a CONTAINER-level subscription: the answer is
    // still applied and the day reloaded from the server.
    final provider = logbookProvider(_logbook.date);
    final keepAlive = ProviderScope.containerOf(context, listen: false).listen(provider, (previous, next) {});
    try {
      final key = _closeIntention.forRequest(formatDate(_logbook.date));
      await ref.read(provider.notifier).closeDay(key: key);
      _closeIntention.accepted();
      if (!mounted) return;
      setState(() => _busy = false);
      showToast(context, 'Jornada cerrada.');
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        if (error.code == 'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS') {
          _missing = missingFromDetails(error.details);
        } else {
          _error = errorMessage(error);
        }
      });
    } finally {
      keepAlive.close();
    }
  }

  Future<void> _reopen() async {
    if (_busy) return;
    final provider = logbookProvider(_logbook.date);
    final reopened = await showReopenDialog(
      context,
      onSubmit: (reason) async {
        final key = _reopenIntention.forRequest('${formatDate(_logbook.date)}|$reason');
        // Held at container level, so it survives even if this widget is unmounted meanwhile
        final keepAlive = ProviderScope.containerOf(context, listen: false).listen(provider, (previous, next) {});
        try {
          await ref.read(provider.notifier).reopenDay(reason: reason, key: key);
          _reopenIntention.accepted();
        } finally {
          keepAlive.close();
        }
      },
    );
    if (reopened && mounted) showToast(context, 'Jornada reabierta.');
  }

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final logbook = _logbook;
    final closed = logbook.closed;

    if (!closed && !canOfferClosing(logbook)) {
      return _Panel(
        key: const Key('closure-panel'),
        closed: false,
        icon: Icons.event_outlined,
        title: 'Cierre de la jornada',
        mobile: mobile,
        body: const Text(
          'Una jornada futura no se cierra: primero hay que vivirla.',
          key: Key('closure-future-note'),
          style: TextStyle(fontSize: 12, height: 1.6, color: AppColors.textSoft),
        ),
      );
    }

    if (closed) {
      final at = logbook.closedAt;
      return _Panel(
        key: const Key('closure-panel'),
        closed: true,
        icon: Icons.lock_outline,
        title: 'Jornada cerrada',
        mobile: mobile,
        action: SecondaryButton(
          key: const Key('closure-reopen'),
          label: 'Reabrir jornada',
          onPressed: _busy ? null : _reopen,
        ),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              at == null ? 'Cerrada.' : 'Cerrada el ${formatDateTime(at)}.',
              key: const Key('closure-closed-at'),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textBody),
            ),
            const SizedBox(height: 4),
            const Text(
              'Para modificar su resumen o sus actividades hay que reabrirla, indicando un motivo. '
              'Las actividades no terminadas siguen disponibles en las jornadas posteriores.',
              style: TextStyle(fontSize: 12, height: 1.6, color: AppColors.textSoft),
            ),
          ],
        ),
      );
    }

    final conditions = closingConditions(widget.day);
    Widget condition(Key key, bool ok, String text) => Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        key: key,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            ok ? Icons.check_circle_outline : Icons.radio_button_unchecked,
            size: 15,
            color: ok ? AppColors.doneText : AppColors.textFaint,
            semanticLabel: ok ? 'Cumplida' : 'Pendiente',
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text, style: const TextStyle(fontSize: 12, height: 1.5, color: AppColors.textBody)),
          ),
        ],
      ),
    );
    return _Panel(
      key: const Key('closure-panel'),
      closed: false,
      icon: Icons.lock_open_outlined,
      title: 'Cierre de la jornada',
      mobile: mobile,
      action: PrimaryButton(
        key: const Key('closure-close'),
        label: 'Cerrar jornada',
        icon: Icons.lock_outline,
        loading: _busy,
        expand: mobile,
        onPressed: _close,
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Cerrarla es una decisión tuya: nunca se cierra sola. Para cerrarla hace falta:',
            style: TextStyle(fontSize: 12, height: 1.6, color: AppColors.textSoft),
          ),
          condition(const Key('closure-condition-summary'), conditions.hasSummary, 'Un resumen con texto'),
          condition(
            const Key('closure-condition-activity'),
            conditions.hasActivity,
            'Al menos una actividad creada en la jornada, o continuada en ella con un avance',
          ),
          if (_missing.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              key: const Key('closure-missing'),
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.pendingBackground,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Semantics(
                liveRegion: true,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Todavía no se puede cerrar',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppColors.pendingText),
                    ),
                    for (final line in _missing)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(line, style: const TextStyle(fontSize: 12, height: 1.5, color: AppColors.pendingText)),
                      ),
                  ],
                ),
              ),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Semantics(
              liveRegion: true,
              child: Text(
                _error!,
                key: const Key('closure-error'),
                style: const TextStyle(fontSize: 12, color: AppColors.error),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// The frame of the closing block: an open day is plain, a closed one is tinted and carries a lock.
class _Panel extends StatelessWidget {
  const _Panel({
    super.key,
    required this.closed,
    required this.icon,
    required this.title,
    required this.body,
    required this.mobile,
    this.action,
  });

  final bool closed;
  final IconData icon;
  final String title;
  final Widget body;
  final bool mobile;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final heading = Row(
      children: [
        Icon(icon, size: 16, color: closed ? AppColors.blockedText : AppColors.textLabel),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            title,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: closed ? AppColors.blockedText : AppColors.textStrong,
            ),
          ),
        ),
      ],
    );
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(mobile ? 14 : 18),
      decoration: BoxDecoration(
        color: closed ? const Color(0xFFFFF7F6) : AppColors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: closed ? const Color(0xFFF3D3D0) : AppColors.border),
      ),
      child: mobile || action == null
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                heading,
                const SizedBox(height: 10),
                body,
                if (action != null) ...[const SizedBox(height: 14), action!],
              ],
            )
          : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [heading, const SizedBox(height: 10), body],
                  ),
                ),
                const SizedBox(width: 18),
                action!,
              ],
            ),
    );
  }
}
