import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const mobile = Size(400, 900);

final yesterday = DateTime.utc(2026, 11, 5);
final tomorrow = DateTime.utc(2026, 11, 7);

Future<void> pumpApp(WidgetTester tester, {required FakeLogbookRepository logbook, Size size = desktop}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
        logbookRepositoryProvider.overrideWithValue(logbook),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  await tester.pumpAndSettle();
}

ProviderContainer containerOf(WidgetTester tester) =>
    ProviderScope.containerOf(tester.element(find.byType(SmartworkApp)));

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> openLogbook(WidgetTester tester) async {
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
  await tapKey(tester, 'nav-logbook');
}

/// Today with one planned activity and the given summary.
({FakeLogbookRepository repo, Activity activity}) withToday({String summary = 'Hoy avancé con el informe'}) {
  final repo = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
  if (summary.isNotEmpty) repo.seedSummary(today, summary);
  return (repo: repo, activity: repo.days[formatDate(today)]!.activities.single);
}

Finder statePill(String label) => find.descendant(of: find.byKey(const Key('logbook-state')), matching: find.text(label));

Future<void> tapClose(WidgetTester tester) => tapKey(tester, 'closure-close');
Future<void> confirm(WidgetTester tester) => tapKey(tester, 'confirm-discard');

Future<void> closeIt(WidgetTester tester) async {
  await tapClose(tester);
  await confirm(tester);
}

/// A closed day, shown.
Future<({FakeLogbookRepository repo, Activity activity})> closedDay(WidgetTester tester, {Size size = desktop}) async {
  final s = withToday();
  s.repo.closeDay(today);
  await pumpApp(tester, logbook: s.repo, size: size);
  await openLogbook(tester);
  return s;
}

Future<void> reopenWith(WidgetTester tester, String reason) async {
  await tapKey(tester, 'closure-reopen');
  await tester.enterText(find.byKey(const Key('reopen-reason')), reason);
  await tapKey(tester, 'reopen-submit');
}

String? errorText(WidgetTester tester, String key) => tester.widget<Text>(find.byKey(Key(key))).data;

void main() {
  setUpAll(loadTestFonts);

  group('an open day', () {
    testWidgets('shows what closing needs and the action to close it', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      expect(find.byKey(const Key('closure-panel')), findsOneWidget);
      expect(find.text('Cierre de la jornada'), findsOneWidget);
      expect(find.byKey(const Key('closure-close')), findsOneWidget);
      expect(find.byKey(const Key('closure-reopen')), findsNothing);
      expect(statePill('Abierta'), findsOneWidget);
      // Both conditions are met: each shows as done
      for (final key in ['closure-condition-summary', 'closure-condition-activity']) {
        expect(
          find.descendant(of: find.byKey(Key(key)), matching: find.bySemanticsLabel('Cumplida')),
          findsOneWidget,
          reason: key,
        );
      }
    });

    testWidgets('marks what is still missing', (tester) async {
      final s = withToday(summary: '');
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      expect(
        find.descendant(of: find.byKey(const Key('closure-condition-summary')), matching: find.bySemanticsLabel('Pendiente')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: find.byKey(const Key('closure-condition-activity')), matching: find.bySemanticsLabel('Cumplida')),
        findsOneWidget,
      );
    });

    testWidgets('a future day is not offered for closing and says so (CA-97)', (tester) async {
      final repo = FakeLogbookRepository()..seed(tomorrow, 'Para mañana');
      repo.seedSummary(tomorrow, 'Notas');
      await pumpApp(tester, logbook: repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await openLogbook(tester);
      expect(find.byKey(const Key('closure-future-note')), findsOneWidget);
      expect(find.byKey(const Key('closure-close')), findsNothing);
      expect(find.byKey(const Key('closure-reopen')), findsNothing);
    });

    testWidgets('a past day can be closed too', (tester) async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'De ayer');
      repo.seedSummary(yesterday, 'Resumen de ayer');
      await pumpApp(tester, logbook: repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(yesterday);
      await tester.pumpAndSettle();
      await openLogbook(tester);
      await closeIt(tester);
      expect(repo.closeRequests.single['date'], '2026-11-05');
      expect(statePill('Cerrada'), findsOneWidget);
    });
  });

  group('closing: what is missing', () {
    testWidgets('without a summary it says so and sends nothing (CA-93)', (tester) async {
      final s = withToday(summary: '');
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(find.byKey(const Key('closure-missing')), findsOneWidget);
      expect(find.textContaining('Falta el resumen de la jornada'), findsOneWidget);
      expect(find.textContaining('Falta una actividad'), findsNothing);
      expect(find.byKey(const Key('confirm-title')), findsNothing); // no confirmation: nothing to confirm
      expect(s.repo.closeRequests, isEmpty);
    });

    testWidgets('a summary of only spaces does not count (CA-94)', (tester) async {
      final s = withToday(summary: '     ');
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(find.textContaining('Falta el resumen de la jornada'), findsOneWidget);
      expect(s.repo.closeRequests, isEmpty);
    });

    testWidgets('without an activity it says so (CA-92)', (tester) async {
      final repo = FakeLogbookRepository();
      await repo.openLogbook(today);
      repo.seedSummary(today, 'Un resumen');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(find.textContaining('Falta una actividad creada en la jornada'), findsOneWidget);
      expect(find.textContaining('Falta el resumen'), findsNothing);
      expect(repo.closeRequests, isEmpty);
    });

    testWidgets('when everything is missing it says everything at once', (tester) async {
      final repo = FakeLogbookRepository();
      await repo.openLogbook(today);
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(find.textContaining('Falta el resumen'), findsOneWidget);
      expect(find.textContaining('Falta una actividad'), findsOneWidget);
    });

    testWidgets('an activity marked as an error does not count (CA-283)', (tester) async {
      final s = withToday();
      s.repo.markAsError(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(find.textContaining('Falta una actividad'), findsOneWidget);
      expect(s.repo.closeRequests, isEmpty);
    });

    testWidgets('a continued activity counts: it has a progress entry of this day (CA-91)', (tester) async {
      final repo = FakeLogbookRepository()..seed(DateTime.utc(2026, 11, 3), 'Empezada hace días');
      final id = repo.days['2026-11-03']!.activities.single.id;
      await repo.registerProgress(
        activityId: id,
        date: today,
        status: ActivityStatus.inProgress,
        description: 'Seguí con ella',
        key: 'k-continued',
      );
      repo.seedSummary(today, 'Hoy la continué');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await closeIt(tester);
      expect(statePill('Cerrada'), findsOneWidget);
    });

    testWidgets('the screen can be wrong: the server has the last word and its details are shown', (tester) async {
      final s = withToday();
      s.repo.closeErrors.add(
        const ApiError(
          code: 'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS',
          message: 'x',
          status: 409,
          details: [
            {'campo': 'resumen', 'motivo': 'vacio'},
          ],
        ),
      );
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await closeIt(tester);
      expect(find.byKey(const Key('closure-missing')), findsOneWidget);
      expect(find.textContaining('Falta el resumen de la jornada'), findsOneWidget);
      expect(find.textContaining('Falta una actividad'), findsNothing);
      expect(statePill('Abierta'), findsOneWidget);
    });
  });

  group('closing', () {
    testWidgets('asks first, and "Todavía no" sends nothing', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(errorText(tester, 'confirm-title'), '¿Cerrar la jornada?');
      expect(errorText(tester, 'confirm-message'), contains('constancia del cierre'));
      await tapKey(tester, 'confirm-keep');
      expect(find.byKey(const Key('confirm-title')), findsNothing);
      expect(s.repo.closeRequests, isEmpty);
      expect(statePill('Abierta'), findsOneWidget);
    });

    testWidgets('confirming sends the real request and the screen shows what the server holds', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await closeIt(tester);

      final request = s.repo.closeRequests.single;
      expect(request['date'], '2026-11-06');
      expect((request['key'] as String).length, 32);
      expect(find.text('Jornada cerrada.'), findsOneWidget); // toast
      expect(statePill('Cerrada'), findsOneWidget);
      expect(find.text('Jornada cerrada'), findsOneWidget); // the panel
      expect(find.byKey(const Key('closure-closed-at')), findsOneWidget);
      expect(find.byKey(const Key('closure-reopen')), findsOneWidget);
      expect(find.byKey(const Key('closure-close')), findsNothing);
      expect(s.repo.audit, [('cierre', null, '2026-11-06')]);
    });

    testWidgets('the activities keep their status and the summary is not editable any more', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await closeIt(tester);
      expect(
        find.descendant(of: find.byKey(Key('status-${s.activity.id}')), matching: find.text('Pendiente')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('summary-edit')), findsNothing);
      expect(find.byKey(const Key('summary-closed-note')), findsOneWidget);
    });

    testWidgets('a closed day looks different: the panel says when it was closed and what to do', (tester) async {
      final s = await closedDay(tester);
      expect(s.repo.days['2026-11-06']!.logbook.closed, isTrue);
      expect(statePill('Cerrada'), findsOneWidget);
      final text = errorText(tester, 'closure-closed-at')!;
      expect(text, startsWith('Cerrada el '));
      expect(find.textContaining('hay que reabrirla'), findsWidgets);
    });

    testWidgets('actions that are not allowed are not offered: progress, but not planning a continuation', (tester) async {
      final s = await closedDay(tester);
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsNothing); // RN-108
      expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsOneWidget); // another, future day
      expect(find.byKey(Key('activity-open-${s.activity.id}')), findsOneWidget); // it can still be read
    });

    testWidgets('the dashboard does not offer progress on the activities of a closed day either', (tester) async {
      final s = withToday();
      s.repo.closeDay(today);
      await pumpApp(tester, logbook: s.repo);
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsNothing);
      expect(find.byKey(Key('activity-open-${s.activity.id}')), findsOneWidget);
    });

    testWidgets('planning on a closed date is not offered: the form says why and cannot be sent (CA-284)', (tester) async {
      final s = withToday();
      s.repo.closeDay(today);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-planning');
      expect(find.byKey(const Key('closed-date-notice')), findsOneWidget);
      await tester.enterText(find.byKey(const Key('plan-title')), 'Otra actividad');
      await tester.ensureVisible(find.byKey(const Key('plan-submit')));
      await tester.tap(find.byKey(const Key('plan-submit')), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(s.repo.days['2026-11-06']!.activities, hasLength(1)); // nothing was sent
      expect(s.repo.calls.where((c) => c.startsWith('create')), isEmpty);
    });

    testWidgets('while it runs it shows loading, ignores a second tap and sends one request', (tester) async {
      final s = withToday();
      final gate = Completer<void>();
      s.repo.closeGate = gate;
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await tapClose(tester);
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pump(); // the request is in flight
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      await tester.tap(find.byKey(const Key('closure-close')), warnIfMissed: false);
      await tester.pump();
      expect(s.repo.closeRequests, hasLength(1));
      gate.complete();
      await tester.pumpAndSettle();
      expect(s.repo.closeRequests, hasLength(1));
      expect(s.repo.audit, hasLength(1));
      expect(statePill('Cerrada'), findsOneWidget);
    });
  });

  group('closing: server errors', () {
    final cases = <(String, int, String)>[
      ('FECHA_FUTURA_NO_PERMITIDA', 422, 'No se puede registrar ejecución ni cerrar una jornada de fecha futura.'),
      ('RECURSO_NO_DISPONIBLE', 404, 'El recurso solicitado no está disponible.'),
      ('SIN_PERTENENCIA_VIGENTE', 403, 'No tienes una pertenencia vigente a un equipo.'),
    ];
    for (final (code, status, message) in cases) {
      testWidgets('$code is explained and the day stays as it was', (tester) async {
        final s = withToday();
        s.repo.closeErrors.add(ApiError(code: code, message: 'x', status: status));
        await pumpApp(tester, logbook: s.repo);
        await openLogbook(tester);
        await closeIt(tester);
        expect(errorText(tester, 'closure-error'), message);
        expect(statePill('Abierta'), findsOneWidget);
        expect(find.byKey(const Key('closure-close')), findsOneWidget); // it can be tried again
      });
    }

    testWidgets('a day closed meanwhile is reloaded: the screen shows it closed', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      s.repo.closeDay(today); // closed from elsewhere
      await tapClose(tester);
      await confirm(tester);
      expect(statePill('Cerrada'), findsOneWidget);
      expect(find.byKey(const Key('closure-reopen')), findsOneWidget);
    });

    testWidgets('a network failure can be retried with the SAME key', (tester) async {
      final s = withToday();
      s.repo.closeErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await closeIt(tester);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      await closeIt(tester);
      expect(find.byKey(const Key('closure-error')), findsNothing);
      final keys = s.repo.closeRequests.map((r) => r['key']).toList();
      expect(keys, hasLength(2));
      expect(keys[0], keys[1]); // one intention: the server recognizes the retry
      expect(s.repo.audit, hasLength(1));
    });

    testWidgets('an expired session sends the user back to the login', (tester) async {
      final s = withToday();
      s.repo.closeErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await closeIt(tester);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('unsaved summary text', () {
    testWidgets('closing asks first about text typed and not saved, because closing judges what is saved', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), 'Texto nuevo sin guardar');
      await tapClose(tester);
      expect(errorText(tester, 'confirm-title'), 'Tienes cambios sin guardar');
      await tapKey(tester, 'confirm-keep'); // "Seguir editando"
      expect(s.repo.closeRequests, isEmpty);
      expect(tester.widget<TextField>(find.byKey(const Key('summary-field'))).controller!.text, 'Texto nuevo sin guardar');
    });

    testWidgets('the whole flow: write the summary, save it, close the day', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await tapClose(tester);
      expect(find.textContaining('Falta el resumen'), findsOneWidget); // nothing sent
      await tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), 'Avancé con el informe y revisé las cifras');
      await tapKey(tester, 'summary-save');
      expect(
        find.descendant(of: find.byKey(const Key('closure-condition-summary')), matching: find.bySemanticsLabel('Cumplida')),
        findsOneWidget,
      );
      await closeIt(tester);
      expect(repo.days['2026-11-06']!.logbook.closed, isTrue);
      expect(find.text('Jornada cerrada.'), findsOneWidget);
      expect(find.byKey(const Key('closure-reopen')), findsOneWidget);
    });
  });

  group('reopening', () {
    testWidgets('is offered on a closed day and asks for the reason', (tester) async {
      await closedDay(tester);
      await tapKey(tester, 'closure-reopen');
      expect(find.byKey(const Key('reopen-title')), findsOneWidget);
      expect(find.byKey(const Key('reopen-reason')), findsOneWidget);
      expect(find.text('Motivo de la reapertura *'), findsOneWidget);
    });

    testWidgets('without a reason it says so and sends nothing (CA-100)', (tester) async {
      final s = await closedDay(tester);
      for (final reason in ['', '   ']) {
        await tapKey(tester, 'closure-reopen');
        await tester.enterText(find.byKey(const Key('reopen-reason')), reason);
        await tapKey(tester, 'reopen-submit');
        expect(find.text('Indica el motivo de la reapertura.'), findsOneWidget, reason: '"$reason"');
        expect(s.repo.reopenRequests, isEmpty);
        await tapKey(tester, 'reopen-cancel');
      }
    });

    testWidgets('Cancelar gives up: nothing is sent and the day stays closed', (tester) async {
      final s = await closedDay(tester);
      await tapKey(tester, 'closure-reopen');
      await tester.enterText(find.byKey(const Key('reopen-reason')), 'Algo');
      await tapKey(tester, 'reopen-cancel');
      expect(find.byKey(const Key('reopen-title')), findsNothing);
      expect(s.repo.reopenRequests, isEmpty);
      expect(statePill('Cerrada'), findsOneWidget);
    });

    testWidgets('with a reason it reopens: the screen shows what the server holds and editing is back', (tester) async {
      final s = await closedDay(tester);
      await reopenWith(tester, '  Olvidé una cifra  ');
      final request = s.repo.reopenRequests.single;
      expect(request['date'], '2026-11-06');
      expect(request['reason'], 'Olvidé una cifra');
      expect((request['key'] as String).length, 32);
      expect(find.byKey(const Key('reopen-title')), findsNothing);
      expect(find.text('Jornada reabierta.'), findsOneWidget);
      expect(statePill('Abierta'), findsOneWidget);
      expect(find.byKey(const Key('closure-close')), findsOneWidget);
      expect(find.byKey(const Key('closure-reopen')), findsNothing);
      expect(s.repo.audit.last, ('reapertura', 'Olvidé una cifra', '2026-11-06'));
    });

    testWidgets('operations are allowed again: edit the summary and register progress', (tester) async {
      final s = await closedDay(tester);
      expect(find.byKey(const Key('summary-edit')), findsNothing);
      await reopenWith(tester, 'Corregir');
      expect(find.byKey(const Key('summary-edit')), findsOneWidget);
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsOneWidget);
      await tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), 'Resumen corregido');
      await tapKey(tester, 'summary-save');
      expect(s.repo.days['2026-11-06']!.logbook.summary, 'Resumen corregido');
    });

    testWidgets('a full cycle: close, reopen, close again — each is its own audit entry (CA-266)', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo);
      await openLogbook(tester);
      await closeIt(tester);
      await reopenWith(tester, 'Primera corrección');
      await closeIt(tester);
      await reopenWith(tester, 'Segunda corrección');
      await closeIt(tester);
      expect(s.repo.audit.map((e) => e.$1), ['cierre', 'reapertura', 'cierre', 'reapertura', 'cierre']);
      expect(s.repo.audit.where((e) => e.$1 == 'reapertura').map((e) => e.$2), ['Primera corrección', 'Segunda corrección']);
      expect(statePill('Cerrada'), findsOneWidget);
      // Each closing used its own key: they are different intentions
      expect(s.repo.closeRequests.map((r) => r['key']).toSet(), hasLength(3));
    });

    testWidgets('a reopened day can only be closed again if it still meets the conditions', (tester) async {
      final s = await closedDay(tester);
      await reopenWith(tester, 'Corregir');
      await tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), '   ');
      await tapKey(tester, 'summary-save');
      await tapClose(tester);
      expect(find.textContaining('Falta el resumen'), findsOneWidget);
      expect(s.repo.closeRequests, isEmpty);
    });

    testWidgets('only the day that was reopened opens: the others stay closed (D-04)', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(yesterday, 'De ayer')
        ..seed(today, 'De hoy');
      repo.seedSummary(yesterday, 'Resumen de ayer');
      repo.seedSummary(today, 'Resumen de hoy');
      repo.closeDay(yesterday);
      repo.closeDay(today);
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await reopenWith(tester, 'Solo hoy');
      expect(repo.days['2026-11-06']!.logbook.closed, isFalse);
      expect(repo.days['2026-11-05']!.logbook.closed, isTrue);
    });
  });

  group('reopening: server errors and retries', () {
    final cases = <(String, int, String)>[
      ('MOTIVO_OBLIGATORIO', 422, 'Indica el motivo.'),
      ('BITACORA_NO_CERRADA', 409, 'La bitácora de esa fecha no está cerrada.'),
      ('TEXTO_DEMASIADO_LARGO', 422, 'El texto supera el máximo permitido.'),
      ('RECURSO_NO_DISPONIBLE', 404, 'El recurso solicitado no está disponible.'),
    ];
    for (final (code, status, message) in cases) {
      testWidgets('$code is explained inside the dialog, which stays open with the reason', (tester) async {
        final s = await closedDay(tester);
        s.repo.reopenErrors.add(ApiError(code: code, message: 'x', status: status));
        await reopenWith(tester, 'Mi motivo');
        expect(errorText(tester, 'reopen-error'), message);
        expect(find.byKey(const Key('reopen-title')), findsOneWidget);
        expect(tester.widget<TextField>(find.byKey(const Key('reopen-reason'))).controller!.text, 'Mi motivo');
        expect(tester.widget<TextField>(find.byKey(const Key('reopen-reason'))).enabled, isTrue);
      });
    }

    testWidgets('a network failure keeps the reason and the retry reuses the SAME key', (tester) async {
      final s = await closedDay(tester);
      s.repo.reopenErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await reopenWith(tester, 'Mi motivo');
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      await tapKey(tester, 'reopen-submit');
      expect(find.byKey(const Key('reopen-title')), findsNothing);
      final keys = s.repo.reopenRequests.map((r) => r['key']).toList();
      expect(keys, hasLength(2));
      expect(keys[0], keys[1]);
      expect(s.repo.audit.where((e) => e.$1 == 'reapertura'), hasLength(1));
    });

    testWidgets('changing the reason gets a NEW key', (tester) async {
      final s = await closedDay(tester);
      s.repo.reopenErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await reopenWith(tester, 'Primer motivo');
      await tester.enterText(find.byKey(const Key('reopen-reason')), 'Otro motivo');
      await tapKey(tester, 'reopen-submit');
      final keys = s.repo.reopenRequests.map((r) => r['key']).toList();
      expect(keys[0], isNot(keys[1]));
    });

    testWidgets('while it runs the dialog shows loading, cannot be closed and sends one request', (tester) async {
      final s = await closedDay(tester);
      final gate = Completer<void>();
      s.repo.reopenGate = gate;
      await tapKey(tester, 'closure-reopen');
      await tester.enterText(find.byKey(const Key('reopen-reason')), 'Mi motivo');
      await tester.tap(find.byKey(const Key('reopen-submit')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(tester.widget<TextField>(find.byKey(const Key('reopen-reason'))).enabled, isFalse);
      await tester.tap(find.byKey(const Key('reopen-submit')), warnIfMissed: false);
      await tester.tap(find.byKey(const Key('reopen-cancel')), warnIfMissed: false);
      await tester.pump();
      expect(find.byKey(const Key('reopen-title')), findsOneWidget); // Cancelar did nothing
      await Navigator.of(tester.element(find.byKey(const Key('reopen-title')))).maybePop(); // nor does a back/dismiss request
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 600));
      expect(find.byKey(const Key('reopen-title')), findsOneWidget);
      expect(s.repo.reopenRequests, hasLength(1));
      gate.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('reopen-title')), findsNothing);
      expect(s.repo.audit.where((e) => e.$1 == 'reapertura'), hasLength(1));
    });

    testWidgets('an expired session closes the dialog and goes back to the login', (tester) async {
      final s = await closedDay(tester);
      s.repo.reopenErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await reopenWith(tester, 'Mi motivo');
      expect(find.byKey(const Key('reopen-title')), findsNothing);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('on a phone', () {
    testWidgets('closing and reopening fit the screen, the dialogs stack their buttons', (tester) async {
      final s = withToday();
      await pumpApp(tester, logbook: s.repo, size: mobile);
      await openLogbook(tester);
      await tapClose(tester);
      final keep = tester.getRect(find.byKey(const Key('confirm-keep')));
      final go = tester.getRect(find.byKey(const Key('confirm-discard')));
      expect(go.top, lessThan(keep.top)); // the main action first
      expect(go.width, greaterThan(250));
      await confirm(tester);
      expect(statePill('Cerrada'), findsOneWidget);
      await tapKey(tester, 'closure-reopen');
      final submit = tester.getRect(find.byKey(const Key('reopen-submit')));
      expect(submit.width, greaterThan(250));
      await tester.enterText(find.byKey(const Key('reopen-reason')), 'Un motivo bastante largo para comprobar que cabe bien en el móvil');
      await tapKey(tester, 'reopen-submit');
      expect(tester.takeException(), isNull);
      expect(statePill('Abierta'), findsOneWidget);
      expect(s.repo.audit.map((e) => e.$1), ['cierre', 'reapertura']);
    });
  });
}
