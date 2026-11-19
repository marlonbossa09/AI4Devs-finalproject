import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/features/logbook/presentation/providers/side_panel.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// "Nueva actividad" side panel (UX-T3): the two forms live in unplanned_form_test.dart and widgets_test.dart for their fields and
/// contract rules; this file covers what the PANEL adds: entries, kinds, one request per intention, unsaved text, what happens after
/// saving, focus and layout.

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final tomorrow = DateTime.utc(2026, 11, 7);

Future<void> pumpApp(
  WidgetTester tester, {
  required FakeLogbookRepository logbook,
  Size size = desktop,
  Role role = Role.collaborator,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
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

/// Opens the sidebar when it is a drawer (phone).
Future<void> openMenu(WidgetTester tester) async {
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) await tapKey(tester, 'menu-toggle');
}

Future<void> openNav(WidgetTester tester, String page) async {
  await openMenu(tester);
  await tapKey(tester, 'nav-$page');
}

Future<void> openPanelFromDashboard(WidgetTester tester) => tapKey(tester, 'dashboard-new-activity');

Future<void> typeTitle(WidgetTester tester, String text) => tester.enterText(find.byKey(const Key('plan-title')), text);

Future<void> savePlanned(WidgetTester tester, {String title = 'Preparar informe', String description = ''}) async {
  await typeTitle(tester, title);
  if (description.isNotEmpty) await tester.enterText(find.byKey(const Key('plan-description')), description);
  await tapKey(tester, 'plan-submit');
}

bool get panelOpen => find.byKey(const Key('side-panel')).evaluate().isNotEmpty;

bool get questionShown => find.byKey(const Key('confirm-title')).evaluate().isNotEmpty;

/// Whether the focused widget is inside the widget that has [key].
bool focusIsInside(String key) {
  var inside = false;
  FocusManager.instance.primaryFocus?.context?.visitAncestorElements((element) {
    if (element.widget.key == Key(key)) inside = true;
    return !inside;
  });
  return inside;
}

Finder inPicker(String day) => find.descendant(of: find.byType(DatePickerDialog), matching: find.text(day));

Future<void> pickPlannedDay(WidgetTester tester, String day) async {
  await tapKey(tester, 'plan-date');
  await tester.tap(inPicker(day));
  await tester.pumpAndSettle();
  await tester.tap(find.text('OK'));
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(loadTestFonts);

  group('entries', () {
    testWidgets('the four screens offer ONE "Nueva actividad" action and no second competing one', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      for (final (page, key) in [
        ('dashboard', 'dashboard-new-activity'),
        ('logbook', 'logbook-new-activity'),
        ('activities', 'activities-new-activity'),
        ('planning', 'planning-new-activity'),
      ]) {
        await openNav(tester, page);
        if (page == 'planning') await tapKey(tester, 'plan-cancel'); // this page opens the panel on its own
        expect(find.byKey(Key(key)), findsOneWidget, reason: page);
        expect(find.text('Nueva actividad'), findsWidgets, reason: page);
        expect(find.textContaining('Actividad no planificada'), findsNothing, reason: '$page has no second action');
        expect(find.text('Nueva planificación'), findsNothing, reason: '$page has no second action');
      }
    });

    for (final (page, key) in [
      ('dashboard', 'dashboard-new-activity'),
      ('logbook', 'logbook-new-activity'),
      ('activities', 'activities-new-activity'),
      ('planning', 'planning-new-activity'),
    ]) {
      testWidgets('from $page the panel opens over the screen without leaving it', (tester) async {
        await pumpApp(tester, logbook: FakeLogbookRepository());
        await openNav(tester, page);
        if (page == 'planning') await tapKey(tester, 'plan-cancel');
        await tapKey(tester, key);
        expect(panelOpen, isTrue);
        expect(find.byKey(const Key('plan-submit')), findsOneWidget); // opens on the planned kind
        expect(find.byKey(Key(key)), findsOneWidget); // the screen is still behind it
        await tapKey(tester, 'plan-cancel');
        expect(panelOpen, isFalse);
        expect(find.byKey(Key(key)), findsOneWidget); // and still there when it closes
      });
    }

    testWidgets('Planificación opens the panel by itself on the planned kind', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openNav(tester, 'planning');
      expect(panelOpen, isTrue);
      expect(find.byKey(const Key('plan-submit')), findsOneWidget);
      expect(find.byKey(const Key('unplanned-submit')), findsNothing);
    });

    testWidgets('the panel names the day it is for in its header and follows the day being looked at', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      expect(find.text('Nueva actividad'), findsWidgets);
      expect(find.descendant(of: find.byKey(const Key('new-activity-date')), matching: find.textContaining(formatTopDate(today))), findsOneWidget);
      await tapKey(tester, 'plan-cancel');

      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await openPanelFromDashboard(tester);
      // A day that has not happened can be planned; what already happened is not "unplanned" for tomorrow
      expect(find.descendant(of: find.byKey(const Key('new-activity-date')), matching: find.textContaining(formatTopDate(tomorrow))), findsOneWidget);
      await tapKey(tester, 'new-activity-type-unplanned');
      expect(find.descendant(of: find.byKey(const Key('new-activity-date')), matching: find.textContaining(formatTopDate(today))), findsOneWidget);
    });

    for (final role in Role.values) {
      testWidgets('a ${role.name} can plan and register in their own logbook from the panel', (tester) async {
        final repo = FakeLogbookRepository();
        await pumpApp(tester, logbook: repo, role: role);
        await openPanelFromDashboard(tester);
        await savePlanned(tester, title: 'Mi plan');
        expect(repo.days[formatDate(today)]!.activities.single.title, 'Mi plan');
        expect(repo.calls.where((c) => c.startsWith('create')), ['create ${formatDate(today)} "Mi plan"']);
      });
    }
  });

  group('the planned kind', () {
    testWidgets('has what M2-03 says: date, title, optional description, the initial status told as text, and nothing about progress', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      expect(find.byKey(const Key('plan-title')), findsOneWidget);
      expect(find.byKey(const Key('plan-date')), findsOneWidget);
      expect(find.byKey(const Key('plan-description')), findsOneWidget);
      expect(find.text('Descripción (opcional)'), findsOneWidget);
      expect(find.text('Estado inicial: Pendiente'), findsOneWidget);
      expect(find.text('Guardar una planificación no registra avances.'), findsOneWidget);
      expect(find.text('Guardar planificación'), findsOneWidget);
      for (final status in ActivityStatus.values) {
        expect(find.byKey(Key('unplanned-status-${status.name}')), findsNothing); // no state to choose
      }
      expect(find.byKey(const Key('unplanned-description')), findsNothing);
      expect(find.textContaining('%'), findsNothing);
      expect(tester.widgetList<TextField>(find.byType(TextField)).where((f) => f.enabled == false), isEmpty);
    });

    testWidgets('the description is optional: a title alone is saved', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Solo título');
      expect(find.text('Descripción (opcional)'), findsNothing); // closed
      final day = repo.days[formatDate(today)]!;
      expect(day.activities.single.title, 'Solo título');
      expect(day.activities.single.status, ActivityStatus.pending);
    });

    testWidgets('the title is required: it is told in the field and nothing is sent', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await tapKey(tester, 'plan-submit');
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      expect(panelOpen, isTrue);
      expect(repo.keys, isEmpty);
    });
  });

  group('one request per intention', () {
    testWidgets('while it is saving there is a spinner without percentage and a second tap does nothing', (tester) async {
      final repo = FakeLogbookRepository()..createGate = Completer<void>();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await typeTitle(tester, 'Preparar informe');
      await tester.tap(find.byKey(const Key('plan-submit')));
      await tester.pump();
      expect(find.descendant(of: find.byKey(const Key('plan-submit')), matching: find.byType(CircularProgressIndicator)), findsOneWidget);
      expect(find.textContaining('%'), findsNothing);
      for (var i = 0; i < 3; i++) {
        await tester.tap(find.byKey(const Key('plan-submit')), warnIfMissed: false);
        await tester.pump();
      }
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pump();
      expect(repo.keys, hasLength(1));
      repo.createGate!.complete();
      await tester.pumpAndSettle();
      expect(repo.keys, hasLength(1));
      expect(repo.days.values.expand((d) => d.activities), hasLength(1));
      expect(panelOpen, isFalse);
    });

    testWidgets('while it is saving the panel cannot be closed (Cancelar, X, Escape and a tap outside do nothing)', (tester) async {
      final repo = FakeLogbookRepository()..createGate = Completer<void>();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await typeTitle(tester, 'Preparar informe');
      await tester.tap(find.byKey(const Key('plan-submit')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('plan-cancel')), warnIfMissed: false);
      await tester.tap(find.byKey(const Key('side-panel-close')), warnIfMissed: false);
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.tapAt(const Offset(300, 400));
      await tester.pump();
      expect(panelOpen, isTrue);
      expect(questionShown, isFalse);
      repo.createGate!.complete();
      await tester.pumpAndSettle();
      expect(panelOpen, isFalse);
    });

    testWidgets('retrying the same content reuses the key; changing the title, the description or the date makes a new one', (tester) async {
      final repo = FakeLogbookRepository()
        ..createErrors.addAll([
          const ApiError(code: ApiError.network, message: 'x'),
          const ApiError(code: ApiError.network, message: 'x'),
          const ApiError(code: ApiError.network, message: 'x'),
          const ApiError(code: ApiError.network, message: 'x'),
          null,
        ]);
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Preparar informe'); // 0: fails
      await tapKey(tester, 'plan-submit'); // 1: same content, fails
      await tester.enterText(find.byKey(const Key('plan-description')), 'Con detalle');
      await tapKey(tester, 'plan-submit'); // 2: description changed, fails
      await typeTitle(tester, 'Preparar el informe');
      await tapKey(tester, 'plan-submit'); // 3: title changed, fails
      await pickPlannedDay(tester, '7');
      await tapKey(tester, 'plan-submit'); // 4: date changed, succeeds
      expect(repo.keys, hasLength(5));
      expect(repo.keys[1], repo.keys[0]);
      expect(repo.keys[2], isNot(repo.keys[1]));
      expect(repo.keys[3], isNot(repo.keys[2]));
      expect(repo.keys[4], isNot(repo.keys[3]));
      expect(repo.days.values.expand((d) => d.activities), hasLength(1)); // however many tries, one activity
    });

    testWidgets('after a success the next planning is a new intention, even with the same content', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Igual');
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Igual');
      expect(repo.keys, hasLength(2));
      expect(repo.keys[0], isNot(repo.keys[1]));
    });

    testWidgets('a recoverable error keeps the panel open with everything typed and says what happened', (tester) async {
      final repo = FakeLogbookRepository()..createErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Preparar informe', description: 'Revisar cifras');
      expect(panelOpen, isTrue);
      expect(find.byKey(const Key('plan-error')), findsOneWidget);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      expect(tester.widget<TextField>(find.byKey(const Key('plan-title'))).controller!.text, 'Preparar informe');
      expect(tester.widget<TextField>(find.byKey(const Key('plan-description'))).controller!.text, 'Revisar cifras');
      expect(tester.widget<TextField>(find.byKey(const Key('plan-title'))).enabled, isTrue);
      expect(repo.days, isEmpty);
    });

    testWidgets('a field error goes away as soon as that field is fixed, and the others stay', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      await tapKey(tester, 'plan-submit');
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      await typeTitle(tester, 'Ya tiene título');
      await tester.pump();
      expect(find.text('El título es obligatorio.'), findsNothing);

      await tapKey(tester, 'new-activity-type-unplanned');
      await tapKey(tester, 'unplanned-submit');
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      expect(find.text('Elige un estado.'), findsOneWidget);
      expect(find.text('Describe el trabajo realizado.'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('unplanned-title')), 'Un título');
      await tester.pump();
      expect(find.text('El título es obligatorio.'), findsNothing);
      expect(find.text('Elige un estado.'), findsOneWidget);
      expect(find.text('Describe el trabajo realizado.'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('unplanned-description')), 'Algo hecho');
      await tester.pump();
      expect(find.text('Describe el trabajo realizado.'), findsNothing);
      expect(find.text('Elige un estado.'), findsOneWidget); // fixed by choosing one, not by typing
    });

    testWidgets('each kind keeps its own typed text when the person switches between them', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      await typeTitle(tester, 'Algo previsto');
      await tapKey(tester, 'new-activity-type-unplanned');
      expect(tester.widget<TextField>(find.byKey(const Key('unplanned-title'))).controller!.text, isEmpty);
      await tester.enterText(find.byKey(const Key('unplanned-title')), 'Algo imprevisto');
      await tapKey(tester, 'new-activity-type-planned');
      expect(tester.widget<TextField>(find.byKey(const Key('plan-title'))).controller!.text, 'Algo previsto');
      await tapKey(tester, 'new-activity-type-unplanned');
      expect(tester.widget<TextField>(find.byKey(const Key('unplanned-title'))).controller!.text, 'Algo imprevisto');
    });
  });

  group('unsaved text: ONE question, whatever way the person leaves', () {
    Future<void> openWithText(WidgetTester tester, FakeLogbookRepository repo, {Size size = desktop}) async {
      await pumpApp(tester, logbook: repo, size: size);
      await openPanelFromDashboard(tester);
      await typeTitle(tester, 'Algo escrito');
    }

    final ways = <(String, Future<void> Function(WidgetTester))>[
      ('Cancelar', (tester) => tester.tap(find.byKey(const Key('plan-cancel')))),
      ('the X', (tester) => tester.tap(find.byKey(const Key('side-panel-close')))),
      ('Escape', (tester) => tester.sendKeyEvent(LogicalKeyboardKey.escape)),
      ('a tap outside the panel', (tester) => tester.tapAt(const Offset(300, 400))),
      ('opening another panel', (tester) async {
        containerOf(tester).read(sidePanelProvider.notifier).open(SidePanelRequest(title: 'Otro', bodyBuilder: (context) => const Text('otro')));
      }),
    ];

    for (final (name, leave) in ways) {
      testWidgets('$name asks once; "Seguir editando" keeps the panel and its text, "Descartar cambios" closes it', (tester) async {
        final repo = FakeLogbookRepository();
        await openWithText(tester, repo);
        await leave(tester);
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('confirm-title')), findsOneWidget);
        expect(find.byKey(const Key('confirm-message')), findsOneWidget);
        await tester.tap(find.byKey(const Key('confirm-keep')));
        await tester.pumpAndSettle();
        expect(questionShown, isFalse);
        expect(panelOpen, isTrue);
        expect(tester.widget<TextField>(find.byKey(const Key('plan-title'))).controller!.text, 'Algo escrito');

        await leave(tester);
        await tester.pumpAndSettle();
        expect(find.byKey(const Key('confirm-title')), findsOneWidget);
        await tester.tap(find.byKey(const Key('confirm-discard')));
        await tester.pumpAndSettle();
        expect(questionShown, isFalse);
        expect(find.byKey(const Key('plan-title')), findsNothing);
        expect(repo.keys, isEmpty); // nothing was saved behind the person's back
      });

      testWidgets('$name closes at once when nothing was typed', (tester) async {
        await pumpApp(tester, logbook: FakeLogbookRepository());
        await openPanelFromDashboard(tester);
        await leave(tester);
        await tester.pumpAndSettle();
        expect(questionShown, isFalse);
        expect(find.byKey(const Key('plan-title')), findsNothing);
      });
    }

    testWidgets('a text of only spaces is not "typed text"', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      await typeTitle(tester, '     ');
      await tapKey(tester, 'plan-cancel');
      expect(questionShown, isFalse);
      expect(panelOpen, isFalse);
    });

    testWidgets('changing page asks once; "Descartar cambios" goes there and closes the panel', (tester) async {
      await openWithText(tester, FakeLogbookRepository());
      await tester.tap(find.byKey(const Key('nav-logbook')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-keep')));
      await tester.pumpAndSettle();
      expect(panelOpen, isTrue);
      expect(find.byKey(const Key('dashboard-new-activity')), findsOneWidget); // still the dashboard

      await tester.tap(find.byKey(const Key('nav-logbook')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pumpAndSettle();
      expect(panelOpen, isFalse);
      expect(find.byKey(const Key('work-date')), findsOneWidget); // Mi bitácora
    });

    testWidgets('signing out asks once; discarding signs out and leaves no panel for the next session', (tester) async {
      await openWithText(tester, FakeLogbookRepository());
      await tester.tap(find.byKey(const Key('logout')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(containerOf(tester).read(sidePanelProvider), isNull);
    });

    testWidgets('the unplanned kind is protected the same way', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      await tapKey(tester, 'new-activity-type-unplanned');
      await tester.enterText(find.byKey(const Key('unplanned-description')), 'Algo hecho');
      await tester.tap(find.byKey(const Key('unplanned-cancel')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
    });

    testWidgets('text in the day summary editor does not make the panel ask when IT closes empty', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openNav(tester, 'logbook');
      await tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), 'Resumen sin guardar');
      await tapKey(tester, 'logbook-new-activity');
      await tapKey(tester, 'plan-cancel');
      expect(questionShown, isFalse); // the panel holds nothing: the summary is not its business
      expect(panelOpen, isFalse);
      expect(tester.widget<TextField>(find.byKey(const Key('summary-field'))).controller!.text, 'Resumen sin guardar');
    });

    testWidgets('with the summary AND the panel holding text, leaving asks ONE question', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openNav(tester, 'logbook');
      await tapKey(tester, 'summary-edit');
      await tester.enterText(find.byKey(const Key('summary-field')), 'Resumen sin guardar');
      await tapKey(tester, 'logbook-new-activity');
      await typeTitle(tester, 'Algo escrito');
      await tester.tap(find.byKey(const Key('nav-activities')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget); // not two dialogs
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pumpAndSettle();
      expect(questionShown, isFalse); // and answering it once is enough
      expect(panelOpen, isFalse);
      expect(find.byKey(const Key('activities-new-activity')), findsOneWidget);
    });
  });

  group('after saving', () {
    testWidgets('the panel closes, the person stays where they were and the screen shows what the server holds', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Ya estaba');
      await pumpApp(tester, logbook: repo);
      await openNav(tester, 'logbook');
      await tapKey(tester, 'logbook-new-activity');
      await savePlanned(tester, title: 'Nueva del día', description: 'Con detalle');
      expect(panelOpen, isFalse);
      expect(find.text('Actividad planificada.'), findsOneWidget);
      expect(find.byKey(const Key('work-date')), findsOneWidget); // still Mi bitácora
      expect(containerOf(tester).read(selectedDateProvider), today);
      expect(find.text('Nueva del día'), findsOneWidget); // refreshed
      expect(find.text('Ya estaba'), findsOneWidget);
    });

    testWidgets('from Actividades the list is refreshed and the person is still on it', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Ya estaba');
      await pumpApp(tester, logbook: repo);
      await openNav(tester, 'activities');
      await tapKey(tester, 'activities-new-activity');
      await savePlanned(tester, title: 'Nueva en la lista');
      expect(panelOpen, isFalse);
      expect(find.byKey(const Key('activities-new-activity')), findsOneWidget);
      expect(find.text('Nueva en la lista'), findsOneWidget);
    });

    testWidgets('from the dashboard its indicators and list follow, with the same day selected', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Del panel principal');
      expect(find.byKey(const Key('dashboard-new-activity')), findsOneWidget);
      expect(find.text('Del panel principal'), findsWidgets);
      expect(containerOf(tester).read(selectedDateProvider), today);
    });

    testWidgets('saved for ANOTHER date: the confirmation names that date and the visible day is not altered', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openNav(tester, 'logbook');
      await tapKey(tester, 'logbook-new-activity');
      await pickPlannedDay(tester, '7');
      await savePlanned(tester, title: 'Para mañana');
      expect(repo.days.keys, [formatDate(tomorrow)]);
      expect(find.text('Actividad planificada para el ${formatShortDate(tomorrow)}.'), findsOneWidget);
      expect(containerOf(tester).read(selectedDateProvider), today); // the day being looked at did not change
      expect(find.text('Para mañana'), findsNothing); // and it is not shown as if it belonged to it
    });

    testWidgets('an unplanned activity saved for a past date says so and stays on the visible day', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await tapKey(tester, 'new-activity-type-unplanned');
      await tapKey(tester, 'unplanned-date');
      await tester.tap(inPicker('5'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('unplanned-title')), 'Del jueves');
      await tester.enterText(find.byKey(const Key('unplanned-description')), 'Lo que hice');
      await tapKey(tester, 'unplanned-status-completed');
      await tapKey(tester, 'unplanned-submit');
      expect(panelOpen, isFalse);
      expect(find.text('Actividad no planificada registrada el ${formatShortDate(DateTime.utc(2026, 11, 5))}.'), findsOneWidget);
      expect(containerOf(tester).read(selectedDateProvider), today);
    });

    testWidgets('a new confirmation never hides the save button of the next panel', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      await savePlanned(tester, title: 'Una');
      expect(find.text('Actividad planificada.'), findsOneWidget);
      await openPanelFromDashboard(tester);
      expect(find.text('Actividad planificada.'), findsNothing); // dismissed when the panel opens
      expect(tester.getRect(find.byKey(const Key('plan-submit'))).bottom, lessThanOrEqualTo(1000));
    });
  });

  group('focus and accessibility', () {
    testWidgets('the focus goes to the first field when the panel opens and back to the button that opened it', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      // Opened with the keyboard: Tab until the button has the focus, then Enter
      for (var i = 0; i < 30 && !focusIsInside('dashboard-new-activity'); i++) {
        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
      }
      expect(focusIsInside('dashboard-new-activity'), isTrue);
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(panelOpen, isTrue);
      expect(tester.widget<TextField>(find.byKey(const Key('plan-title'))).focusNode!.hasFocus, isTrue);
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(panelOpen, isFalse);
      expect(focusIsInside('dashboard-new-activity'), isTrue);
    });

    testWidgets('the two kinds are an exclusive group of buttons that say which one is selected, not only by color', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      final planned = tester.getSemantics(find.byKey(const Key('new-activity-type-planned')));
      final unplanned = tester.getSemantics(find.byKey(const Key('new-activity-type-unplanned')));
      expect(planned.flagsCollection.isButton, isTrue);
      expect(planned.flagsCollection.isSelected, isTrue);
      expect(unplanned.flagsCollection.isSelected, isFalse);
      expect(planned.label, contains('Planificada'));
      await tapKey(tester, 'new-activity-type-unplanned');
      expect(tester.getSemantics(find.byKey(const Key('new-activity-type-unplanned'))).flagsCollection.isSelected, isTrue);
      expect(tester.getSemantics(find.byKey(const Key('new-activity-type-planned'))).flagsCollection.isSelected, isFalse);
      handle.dispose();
    });

    testWidgets('the keyboard reaches the fields and the actions of the panel in order, and nothing of the page behind', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openPanelFromDashboard(tester);
      final seen = <String>[];
      for (var i = 0; i < 12; i++) {
        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        for (final key in ['plan-title', 'plan-date', 'plan-description', 'plan-cancel', 'plan-submit', 'side-panel-close']) {
          if (focusIsInside(key) && (seen.isEmpty || seen.last != key)) seen.add(key);
        }
        expect(focusIsInside('dashboard-new-activity'), isFalse, reason: 'the page behind is out of reach');
        expect(focusIsInside('nav-dashboard'), isFalse, reason: 'the sidebar is out of reach');
      }
      expect(seen, containsAll(['plan-title', 'plan-cancel', 'plan-submit']));
    });

    testWidgets('an error is shown inside the field that has it, and a server error is announced as it appears', (tester) async {
      final handle = tester.ensureSemantics();
      final repo = FakeLogbookRepository()..createErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openPanelFromDashboard(tester);
      await tapKey(tester, 'plan-submit');
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      await savePlanned(tester, title: 'Algo');
      final error = tester.getSemantics(find.byKey(const Key('plan-error')));
      expect(error.flagsCollection.isLiveRegion, isTrue);
      handle.dispose();
    });
  });

  group('layout', () {
    testWidgets('desktop and tablet: 480 px wide on the right, the action strip fixed under a body that scrolls', (tester) async {
      for (final size in [desktop, tablet]) {
        await pumpApp(tester, logbook: FakeLogbookRepository(), size: size);
        await openPanelFromDashboard(tester);
        final panel = tester.getRect(find.byKey(const Key('side-panel')));
        expect(panel.width, 480);
        expect(panel.right, size.width);
        final actions = tester.getRect(find.byKey(const Key('side-panel-actions')));
        expect(actions.bottom, closeTo(size.height, 1)); // pinned to the bottom edge
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'plan-cancel');
      }
    });

    testWidgets('mobile: full screen, with both actions in the fixed strip, and the whole unplanned flow fits', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo, size: mobile);
      await openPanelFromDashboard(tester);
      expect(tester.getSize(find.byKey(const Key('side-panel'))).width, 400);
      expect(tester.getRect(find.byKey(const Key('side-panel-actions'))).bottom, closeTo(900, 1));
      expect(find.byKey(const Key('plan-cancel')), findsOneWidget);
      await tapKey(tester, 'new-activity-type-unplanned');
      await tester.enterText(find.byKey(const Key('unplanned-title')), 'Un imprevisto con un título bastante largo para comprobar el ajuste en pantallas estrechas');
      await tester.enterText(find.byKey(const Key('unplanned-description')), 'Una descripción también larga para ver cómo se parte en varias líneas dentro del panel');
      await tapKey(tester, 'unplanned-status-blocked');
      await tester.enterText(find.byKey(const Key('unplanned-reason')), 'Falta el acceso al servidor de pruebas');
      await tapKey(tester, 'unplanned-submit');
      expect(repo.days.values.expand((d) => d.activities).single.status, ActivityStatus.blocked);
      expect(tester.takeException(), isNull);
    });

    testWidgets('with a larger text size the two actions wrap instead of overflowing', (tester) async {
      tester.view.physicalSize = const Size(520, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      tester.platformDispatcher.textScaleFactorTestValue = 1.6;
      addTearDown(tester.platformDispatcher.clearAllTestValues);
      await tester.pumpWidget(
        ProviderScope(
          retry: noAutomaticRetry,
          overrides: [
            authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
            logbookRepositoryProvider.overrideWithValue(FakeLogbookRepository()),
          ],
          child: const SmartworkApp(webFonts: false),
        ),
      );
      await tester.pumpAndSettle();
      await openPanelFromDashboard(tester);
      expect(find.byKey(const Key('plan-submit')), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
