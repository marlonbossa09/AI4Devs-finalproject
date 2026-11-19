import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';
import 'closure_test.dart' as c;

bool enabled(WidgetTester tester, String key) =>
    tester.widget<FilledButton>(find.descendant(of: find.byKey(Key(key)), matching: find.byType(FilledButton))).onPressed != null;

/// Picks a day of November 2026 in the calendar of the date field [key].
Future<void> pickDay(WidgetTester tester, String key, String day) async {
  await c.tapKey(tester, key);
  await tester.tap(find.text(day));
  await tester.pumpAndSettle();
  await tester.tap(find.text('OK'));
  await tester.pumpAndSettle();
}

/// Picks a day of November 2026 in the calendar of the date field [key], without waiting for animations
/// to stop (a request may be running, with its spinner).
Future<void> pickDayWhileBusy(WidgetTester tester, String key, String day) async {
  await tester.ensureVisible(find.byKey(Key(key)));
  await tester.pump(const Duration(milliseconds: 600));
  await tester.tap(find.byKey(Key(key)));
  await tester.pump(const Duration(milliseconds: 400));
  await tester.tap(find.text(day));
  await tester.pump(const Duration(milliseconds: 200));
  await tester.tap(find.text('OK'));
  await tester.pump(const Duration(seconds: 1)); // the other day loads
  await tester.pump(const Duration(seconds: 1));
}

void main() {
  setUpAll(loadTestFonts);

  group('the forms do not offer what a closed day forbids', () {
    testWidgets('planning: the notice shows and sending is not offered; another date works again', (tester) async {
      final s = c.withToday();
      s.repo.closeDay(today);
      await c.pumpApp(tester, logbook: s.repo);
      await c.tapKey(tester, 'nav-planning');
      expect(find.byKey(const Key('closed-date-notice')), findsOneWidget);
      expect(find.textContaining('está cerrada'), findsWidgets);
      expect(enabled(tester, 'plan-submit'), isFalse);
      await pickDay(tester, 'plan-date', '7'); // tomorrow: it has no logbook, so it is not closed
      expect(find.byKey(const Key('closed-date-notice')), findsNothing);
      expect(enabled(tester, 'plan-submit'), isTrue);
      await tester.enterText(find.byKey(const Key('plan-title')), 'Para mañana');
      await c.tapKey(tester, 'plan-submit');
      expect(s.repo.days['2026-11-07']!.activities.single.title, 'Para mañana');
    });

    testWidgets('unplanned activity: the notice shows and sending is not offered', (tester) async {
      final s = c.withToday();
      s.repo.closeDay(today);
      await c.pumpApp(tester, logbook: s.repo);
      await c.openLogbook(tester);
      await c.tapKey(tester, 'logbook-new-activity');
      await c.tapKey(tester, 'new-activity-type-unplanned');
      expect(find.byKey(const Key('closed-date-notice')), findsOneWidget);
      expect(enabled(tester, 'unplanned-submit'), isFalse);
      await pickDay(tester, 'unplanned-date', '5'); // yesterday: no logbook
      expect(find.byKey(const Key('closed-date-notice')), findsNothing);
      expect(enabled(tester, 'unplanned-submit'), isTrue);
    });

    testWidgets('progress: from the activity detail the notice shows for a closed date', (tester) async {
      final s = c.withToday();
      s.repo.closeDay(today);
      await c.pumpApp(tester, logbook: s.repo);
      await c.openLogbook(tester);
      await c.tapKey(tester, 'activity-open-${s.activity.id}');
      await c.tapKey(tester, 'detail-register-progress');
      expect(find.byKey(const Key('closed-date-notice')), findsOneWidget);
      expect(enabled(tester, 'progress-submit'), isFalse);
      await pickDay(tester, 'progress-date', '5'); // a past date with no logbook: a retroactive entry
      expect(find.byKey(const Key('closed-date-notice')), findsNothing);
      expect(enabled(tester, 'progress-submit'), isTrue);
    });

    testWidgets('an open date shows no notice and offers sending', (tester) async {
      final s = c.withToday();
      await c.pumpApp(tester, logbook: s.repo);
      await c.tapKey(tester, 'nav-planning');
      expect(find.byKey(const Key('closed-date-notice')), findsNothing);
      expect(enabled(tester, 'plan-submit'), isTrue);
    });

    testWidgets('a screen that was out of date: the server rejects, the answer is explained and the notice appears', (
      tester,
    ) async {
      final s = c.withToday();
      await c.pumpApp(tester, logbook: s.repo);
      await c.tapKey(tester, 'nav-planning');
      expect(enabled(tester, 'plan-submit'), isTrue);
      s.repo.closeDay(today); // closed from another device
      await tester.enterText(find.byKey(const Key('plan-title')), 'Otra actividad');
      await c.tapKey(tester, 'plan-submit');
      expect(
        c.errorText(tester, 'plan-error'),
        'La bitácora de esa fecha está cerrada. Hay que reabrirla antes de modificarla.',
      );
      expect(s.repo.days['2026-11-06']!.activities, hasLength(1)); // the server did not add it
      expect(find.byKey(const Key('closed-date-notice')), findsOneWidget); // the day was reloaded: now it knows
      expect(enabled(tester, 'plan-submit'), isFalse);
    });
  });

  group('the state of the day changes while the user is working', () {
    testWidgets('reopening a day that was already reopened elsewhere: the dialog explains and the panel updates', (
      tester,
    ) async {
      final s = await c.closedDay(tester);
      s.repo.reopenErrors.add(const ApiError(code: 'BITACORA_NO_CERRADA', message: 'x', status: 409));
      await c.reopenWith(tester, 'Corregir');
      expect(c.errorText(tester, 'reopen-error'), 'La bitácora de esa fecha no está cerrada.');
      await c.tapKey(tester, 'reopen-cancel');
    });

    testWidgets('closing a day that was closed elsewhere: the screen shows it closed, with no error', (tester) async {
      final s = c.withToday();
      await c.pumpApp(tester, logbook: s.repo);
      await c.openLogbook(tester);
      s.repo.closeDay(today);
      await c.tapKey(tester, 'closure-close');
      await c.confirm(tester);
      expect(c.statePill('Cerrada'), findsOneWidget);
      expect(find.byKey(const Key('closure-reopen')), findsOneWidget);
      expect(find.byKey(const Key('closure-error')), findsNothing);
    });

    testWidgets('the summary editor leaves when the day is closed elsewhere and the save is rejected', (tester) async {
      final s = c.withToday();
      await c.pumpApp(tester, logbook: s.repo);
      await c.openLogbook(tester);
      await c.tapKey(tester, 'summary-edit');
      s.repo.closeDay(today);
      await tester.enterText(find.byKey(const Key('summary-field')), 'Texto nuevo');
      await c.tapKey(tester, 'summary-save');
      expect(find.byKey(const Key('summary-field')), findsNothing); // the day was reloaded: closed
      expect(c.statePill('Cerrada'), findsOneWidget);
      expect(s.repo.days['2026-11-06']!.logbook.summary, 'Hoy avancé con el informe'); // not overwritten
    });
  });

  group('the date changes while an operation runs', () {
    testWidgets('closing: the answer is still applied to the day it was for, with no error', (tester) async {
      final s = c.withToday();
      final gate = Completer<void>();
      s.repo.closeGate = gate;
      await c.pumpApp(tester, logbook: s.repo);
      await c.openLogbook(tester);
      await c.tapKey(tester, 'closure-close');
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pump(const Duration(milliseconds: 400)); // in flight
      await pickDayWhileBusy(tester, 'work-date', '5'); // yesterday
      expect(find.byKey(const Key('no-logbook')), findsOneWidget); // the screen moved on
      gate.complete();
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(s.repo.audit, [('cierre', null, '2026-11-06')]); // closed exactly once, on its own day
      expect(s.repo.closeRequests, hasLength(1));
      // Coming back, the day is shown as the server holds it: closed
      c.containerOf(tester).read(selectedDateProvider.notifier).select(today);
      await tester.pumpAndSettle();
      expect(c.statePill('Cerrada'), findsOneWidget);
    });

    testWidgets('saving the summary: the text is saved on its own day even if the user moved to another', (tester) async {
      final s = c.withToday();
      final gate = Completer<void>();
      s.repo.summaryGate = gate;
      await c.pumpApp(tester, logbook: s.repo);
      await c.openLogbook(tester);
      await c.tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), 'Resumen escrito antes de cambiar de día');
      await tester.ensureVisible(find.byKey(const Key('summary-save')));
      await tester.tap(find.byKey(const Key('summary-save')));
      await tester.pump(const Duration(milliseconds: 400)); // in flight
      await pickDayWhileBusy(tester, 'work-date', '5'); // asks first: the text is not saved yet
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-discard'))); // "Descartar cambios": leave anyway
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
      gate.complete();
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(s.repo.days['2026-11-06']!.logbook.summary, 'Resumen escrito antes de cambiar de día');
      c.containerOf(tester).read(selectedDateProvider.notifier).select(today);
      await tester.pumpAndSettle();
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Resumen escrito antes de cambiar de día');
    });

    testWidgets('reopening: the dialog is modal, so the date cannot change under it', (tester) async {
      final s = await c.closedDay(tester);
      final gate = Completer<void>();
      s.repo.reopenGate = gate;
      await c.tapKey(tester, 'closure-reopen');
      await tester.enterText(find.byKey(const Key('reopen-reason')), 'Corregir');
      await tester.tap(find.byKey(const Key('reopen-submit')));
      await tester.pump(const Duration(milliseconds: 400));
      await tester.tap(find.byKey(const Key('work-date')), warnIfMissed: false); // behind the dialog: nothing happens
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('OK'), findsNothing); // no calendar opened
      gate.complete();
      await tester.pumpAndSettle();
      expect(c.statePill('Abierta'), findsOneWidget);
      expect(s.repo.audit.where((e) => e.$1 == 'reapertura'), hasLength(1));
    });
  });
}
