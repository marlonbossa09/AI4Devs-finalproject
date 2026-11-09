import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/presentation/providers/auth.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_notifier.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const mobile = Size(400, 900);

final yesterday = DateTime.utc(2026, 11, 5);

Future<void> pumpApp(
  WidgetTester tester, {
  required FakeLogbookRepository logbook,
  FakeAuthRepository? auth,
  Size size = desktop,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(auth ?? FakeAuthRepository(session: sampleSession())),
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
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
}

Future<void> openLogbook(WidgetTester tester) async {
  await openMenu(tester);
  await tapKey(tester, 'nav-logbook');
}

Future<void> startEditing(WidgetTester tester) => tapKey(tester, 'summary-edit');

Future<void> type(WidgetTester tester, String text) => tester.enterText(find.byKey(const Key('summary-field')), text);

String fieldText(WidgetTester tester) => tester.widget<TextField>(find.byKey(const Key('summary-field'))).controller!.text;

Future<void> pickDay(WidgetTester tester, String key, String day) async {
  await tapKey(tester, key);
  await tester.tap(find.text(day));
  await tester.pumpAndSettle();
  await tester.tap(find.text('OK'));
  await tester.pumpAndSettle();
}

bool get dialogShown => find.byKey(const Key('confirm-title')).evaluate().isNotEmpty;

FakeLogbookRepository withDay({String summary = ''}) {
  final repo = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
  if (summary.isNotEmpty) repo.seedSummary(today, summary);
  return repo;
}

/// Mi bitácora with the editor open and `text` typed (unsaved).
Future<FakeLogbookRepository> editingWith(
  WidgetTester tester, {
  String saved = 'Resumen guardado',
  String text = 'Texto nuevo sin guardar',
  Size size = desktop,
  FakeAuthRepository? auth,
}) async {
  final repo = withDay(summary: saved);
  await pumpApp(tester, logbook: repo, auth: auth, size: size);
  await openLogbook(tester);
  await startEditing(tester);
  await type(tester, text);
  return repo;
}

void main() {
  setUpAll(loadTestFonts);

  group('changing the date', () {
    testWidgets('asks first when there is unsaved text, and says what is at stake', (tester) async {
      await editingWith(tester);
      await pickDay(tester, 'work-date', '5');
      expect(dialogShown, isTrue);
      expect(tester.widget<Text>(find.byKey(const Key('confirm-title'))).data, 'Tienes cambios sin guardar');
      expect(tester.widget<Text>(find.byKey(const Key('confirm-message'))).data, contains('se perderá'));
      expect(find.text('Seguir editando'), findsOneWidget);
      expect(find.text('Descartar cambios'), findsOneWidget);
    });

    testWidgets('"Seguir editando" keeps the date, the editor and the typed text', (tester) async {
      await editingWith(tester);
      await pickDay(tester, 'work-date', '5');
      await tapKey(tester, 'confirm-keep');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), today);
      expect(fieldText(tester), 'Texto nuevo sin guardar');
      expect(find.text(formatShortDate(today)), findsWidgets);
    });

    testWidgets('"Descartar cambios" goes to the chosen date and drops the typed text', (tester) async {
      final repo = await editingWith(tester);
      await pickDay(tester, 'work-date', '5');
      await tapKey(tester, 'confirm-discard');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), yesterday);
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
      expect(find.byKey(const Key('summary-field')), findsNothing);
      expect(repo.summaryRequests, isEmpty); // nothing was saved behind the user's back
      // Coming back, the day shows what the server holds, not the discarded text
      await pickDay(tester, 'work-date', '6');
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Resumen guardado');
      expect(find.byKey(const Key('summary-field')), findsNothing);
    });

    testWidgets('Escape and tapping outside the question also keep the text', (tester) async {
      await editingWith(tester);
      await pickDay(tester, 'work-date', '5');
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), today);
      expect(fieldText(tester), 'Texto nuevo sin guardar');

      await pickDay(tester, 'work-date', '5');
      await tester.tapAt(const Offset(5, 5)); // outside the dialog
      await tester.pumpAndSettle();
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), today);
    });

    testWidgets('does not ask when the editor was only opened', (tester) async {
      final repo = withDay(summary: 'Resumen guardado');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await startEditing(tester);
      await pickDay(tester, 'work-date', '5');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), yesterday);
    });

    testWidgets('does not ask when the text was typed and then put back as saved', (tester) async {
      await editingWith(tester, text: 'Otra cosa');
      await type(tester, 'Resumen guardado');
      await pickDay(tester, 'work-date', '5');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), yesterday);
    });

    testWidgets('does not ask once the text is saved', (tester) async {
      await editingWith(tester);
      await tapKey(tester, 'summary-save');
      expect(find.text('Resumen guardado.'), findsOneWidget); // toast
      await pickDay(tester, 'work-date', '5');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), yesterday);
    });

    testWidgets('does not ask when no editor is open', (tester) async {
      await pumpApp(tester, logbook: withDay(summary: 'Resumen guardado'));
      await openLogbook(tester);
      await pickDay(tester, 'work-date', '5');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(selectedDateProvider), yesterday);
    });
  });

  group('leaving Mi bitácora', () {
    testWidgets('the sidebar asks first; keeping stays in the logbook with the text', (tester) async {
      await editingWith(tester);
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isTrue);
      await tapKey(tester, 'confirm-keep');
      expect(containerOf(tester).read(currentPageProvider), AppPage.logbook);
      expect(fieldText(tester), 'Texto nuevo sin guardar');
    });

    testWidgets('the sidebar asks first; discarding goes where the user asked', (tester) async {
      final repo = await editingWith(tester);
      await tapKey(tester, 'nav-dashboard');
      await tapKey(tester, 'confirm-discard');
      expect(containerOf(tester).read(currentPageProvider), AppPage.dashboard);
      expect(find.byKey(const Key('dashboard-new-planning')), findsOneWidget);
      expect(repo.summaryRequests, isEmpty);
      // Back in Mi bitácora the editor is closed and the saved text is there
      await openLogbook(tester);
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Resumen guardado');
      expect(find.byKey(const Key('summary-field')), findsNothing);
    });

    testWidgets('the buttons of the page ask too: new planning, unplanned activity, progress, detail', (tester) async {
      final repo = await editingWith(tester);
      final id = repo.days[formatDate(today)]!.activities.single.id;
      for (final (key, page) in [
        ('logbook-new-planning', AppPage.planning),
        ('logbook-new-unplanned', AppPage.unplanned),
        ('progress-action-$id', AppPage.progress),
        ('continuation-action-$id', AppPage.continuation),
        ('activity-open-$id', AppPage.activityDetail),
      ]) {
        await tapKey(tester, key);
        expect(dialogShown, isTrue, reason: key);
        expect(containerOf(tester).read(currentPageProvider), AppPage.logbook, reason: key);
        await tapKey(tester, 'confirm-keep');
        expect(fieldText(tester), 'Texto nuevo sin guardar', reason: key);
        // And discarding does go there
        await tapKey(tester, key);
        await tapKey(tester, 'confirm-discard');
        expect(containerOf(tester).read(currentPageProvider), page, reason: key);
        containerOf(tester).read(currentPageProvider.notifier).go(AppPage.logbook);
        await tester.pumpAndSettle();
        await startEditing(tester);
        await type(tester, 'Texto nuevo sin guardar');
      }
    });

    testWidgets('does not ask when nothing would be lost', (tester) async {
      await pumpApp(tester, logbook: withDay(summary: 'Resumen guardado'));
      await openLogbook(tester);
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(currentPageProvider), AppPage.dashboard);
    });

    testWidgets('does not ask after saving', (tester) async {
      await editingWith(tester);
      await tapKey(tester, 'summary-save');
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isFalse);
      expect(containerOf(tester).read(currentPageProvider), AppPage.dashboard);
    });

    testWidgets('a save that fails leaves the text unsaved, so leaving still asks', (tester) async {
      final repo = await editingWith(tester);
      repo.summaryErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await tapKey(tester, 'summary-save');
      expect(find.byKey(const Key('summary-error')), findsOneWidget);
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isTrue);
    });

    testWidgets('a day closed meanwhile leaves the editor and nothing is asked', (tester) async {
      final repo = await editingWith(tester);
      repo.closeDay(today);
      containerOf(tester).invalidate(logbookProvider(today));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('summary-field')), findsNothing);
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isFalse);
    });
  });

  group('signing out', () {
    testWidgets('asks first; keeping stays signed in', (tester) async {
      final auth = FakeAuthRepository(session: sampleSession());
      await editingWith(tester, auth: auth);
      await tapKey(tester, 'logout');
      expect(dialogShown, isTrue);
      await tapKey(tester, 'confirm-keep');
      expect(auth.logoutCalls, 0);
      expect(fieldText(tester), 'Texto nuevo sin guardar');
    });

    testWidgets('asks first; discarding signs out', (tester) async {
      final auth = FakeAuthRepository(session: sampleSession());
      await editingWith(tester, auth: auth);
      await tapKey(tester, 'logout');
      await tapKey(tester, 'confirm-discard');
      expect(auth.logoutCalls, 1);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });

    testWidgets('does not ask when there is nothing unsaved', (tester) async {
      final auth = FakeAuthRepository(session: sampleSession());
      await pumpApp(tester, logbook: withDay(), auth: auth);
      await tapKey(tester, 'logout');
      expect(dialogShown, isFalse);
      expect(auth.logoutCalls, 1);
    });

    testWidgets('a session that expires while the question is open closes the question', (tester) async {
      await editingWith(tester);
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isTrue);
      containerOf(tester).read(authProvider.notifier).expired();
      await tester.pumpAndSettle();
      expect(dialogShown, isFalse);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('closing the editor', () {
    testWidgets('Cancelar with changes asks; keeping leaves the editor and the text', (tester) async {
      await editingWith(tester);
      await tapKey(tester, 'summary-cancel');
      expect(dialogShown, isTrue);
      expect(tester.widget<Text>(find.byKey(const Key('confirm-message'))).data, contains('cierras el editor'));
      await tapKey(tester, 'confirm-keep');
      expect(fieldText(tester), 'Texto nuevo sin guardar');
    });

    testWidgets('Cancelar with changes asks; discarding closes the editor and shows the saved text', (tester) async {
      final repo = await editingWith(tester);
      await tapKey(tester, 'summary-cancel');
      await tapKey(tester, 'confirm-discard');
      expect(find.byKey(const Key('summary-field')), findsNothing);
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Resumen guardado');
      expect(repo.summaryRequests, isEmpty);
    });

    testWidgets('Cancelar without changes closes the editor with no question', (tester) async {
      await pumpApp(tester, logbook: withDay(summary: 'Resumen guardado'));
      await openLogbook(tester);
      await startEditing(tester);
      await tapKey(tester, 'summary-cancel');
      expect(dialogShown, isFalse);
      expect(find.byKey(const Key('summary-field')), findsNothing);
    });
  });

  group('on a phone', () {
    testWidgets('the question fits, stacks its buttons and protects the text', (tester) async {
      await editingWith(tester, size: mobile);
      await openMenu(tester);
      await tapKey(tester, 'nav-dashboard');
      expect(dialogShown, isTrue);
      final keep = tester.getRect(find.byKey(const Key('confirm-keep')));
      final discard = tester.getRect(find.byKey(const Key('confirm-discard')));
      expect(keep.top, lessThan(discard.top)); // stacked, the safe option first
      expect(keep.width, greaterThan(250)); // full width: easy to tap
      expect(tester.takeException(), isNull);
      await tapKey(tester, 'confirm-keep');
      expect(fieldText(tester), 'Texto nuevo sin guardar');
    });
  });
}
