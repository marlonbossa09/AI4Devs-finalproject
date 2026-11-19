import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/features/logbook/presentation/widgets/activity_tile.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// Mi bitácora (UX-T5): the day and its state first, the activities next, the summary, the closing and the audit around them.
/// The rules of the summary, the closing and the activities live in their own test files; this one covers the page's layout,
/// the date controls and the filter.

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final tomorrow = DateTime.utc(2026, 11, 7);
final yesterday = DateTime.utc(2026, 11, 5);

Future<void> pumpLogbook(WidgetTester tester, FakeLogbookRepository repo, {Size size = desktop}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
        logbookRepositoryProvider.overrideWithValue(repo),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  await tester.pumpAndSettle();
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
  await tester.tap(find.byKey(const Key('nav-logbook')));
  await tester.pumpAndSettle();
}

ProviderContainer containerOf(WidgetTester tester) =>
    ProviderScope.containerOf(tester.element(find.byType(SmartworkApp)));

FakeLogbookRepository mixedDay() {
  final repo = FakeLogbookRepository()
    ..seed(today, 'Revisar propuesta', description: 'Leer y comentar')
    ..seed(today, 'Entregar informe', status: ActivityStatus.completed);
  final key = formatDate(today);
  final day = repo.days[key]!;
  repo.days[key] = LogbookDay(
    logbook: day.logbook,
    plannings: day.plannings,
    activities: [
      ...day.activities,
      Activity(
        id: 'u1',
        userId: 'p1',
        title: 'Atender incidente',
        origin: ActivityOrigin.unplanned,
        status: ActivityStatus.inProgress,
        date: today,
        createdAt: DateTime.utc(2026, 11, 6, 16),
      ),
    ],
  );
  return repo;
}

Offset at(WidgetTester tester, Finder finder) => tester.getTopLeft(finder);

void main() {
  setUpAll(loadTestFonts);

  group('the day first', () {
    testWidgets('the date and the state of the day are right under the title, before the activities', (tester) async {
      await pumpLogbook(tester, mixedDay());
      final date = at(tester, find.byKey(const Key('work-date'))).dy;
      final state = at(tester, find.byKey(const Key('logbook-state'))).dy;
      final activities = at(tester, find.byKey(const Key('activities-heading'))).dy;
      expect(date, lessThan(state));
      expect(state, lessThan(activities));
      expect(activities, lessThan(400)); // the activities start high on the screen
      expect(find.text('Abierta'), findsOneWidget);
      expect(find.text('Jornada actual'), findsOneWidget);
    });

    testWidgets('a closed day says "Cerrada" in the same place and offers to reopen it, and nothing else about the state contradicts it', (tester) async {
      final repo = mixedDay()..closeDay(today);
      await pumpLogbook(tester, repo);
      expect(find.descendant(of: find.byKey(const Key('logbook-state')), matching: find.text('Cerrada')), findsOneWidget);
      expect(find.text('Abierta'), findsNothing);
      expect(find.byKey(const Key('closure-reopen')), findsOneWidget);
      expect(find.byKey(const Key('closure-close')), findsNothing);
    });

    testWidgets('there is ONE "Nueva actividad" action, and it opens the panel', (tester) async {
      await pumpLogbook(tester, mixedDay());
      expect(find.text('Nueva actividad'), findsOneWidget);
      expect(find.textContaining('Nueva actividad →'), findsNothing);
      await tester.tap(find.byKey(const Key('logbook-new-activity')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsOneWidget);
    });

    testWidgets('the previous and next day buttons move the date by one day and load that day', (tester) async {
      final repo = mixedDay();
      await pumpLogbook(tester, repo);
      await tester.tap(find.byKey(const Key('date-next')));
      await tester.pumpAndSettle();
      expect(containerOf(tester).read(selectedDateProvider), tomorrow);
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
      await tester.tap(find.byKey(const Key('date-previous')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('date-previous')));
      await tester.pumpAndSettle();
      expect(containerOf(tester).read(selectedDateProvider), yesterday);
      expect(repo.calls, containsAll(['get 2026-11-07', 'get 2026-11-05']));
    });

    testWidgets('the day buttons ask first when there is unsaved summary text, like the date field', (tester) async {
      await pumpLogbook(tester, mixedDay());
      await tester.tap(find.byKey(const Key('summary-edit')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('summary-field')), 'Texto sin guardar');
      await tester.tap(find.byKey(const Key('date-next')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      expect(containerOf(tester).read(selectedDateProvider), today);
      await tester.tap(find.byKey(const Key('confirm-keep')));
      await tester.pumpAndSettle();
      expect(containerOf(tester).read(selectedDateProvider), today);
      expect(find.byKey(const Key('summary-field')), findsOneWidget);
    });
  });

  group('the activities', () {
    testWidgets('no activity shows a clock time or a duration', (tester) async {
      await pumpLogbook(tester, mixedDay());
      final inTiles = find.byType(ActivityTile);
      expect(inTiles, findsNWidgets(3));
      expect(find.descendant(of: inTiles, matching: find.textContaining(RegExp(r'\d{1,2}:\d{2}'))), findsNothing);
      expect(find.descendant(of: inTiles, matching: find.textContaining(RegExp(r'\d+ ?(min|h)\b'))), findsNothing);
    });

    testWidgets('the filter counts what the day returned and filters by how the activities started', (tester) async {
      await pumpLogbook(tester, mixedDay());
      expect(find.text('Todas 3'), findsOneWidget);
      expect(find.text('Planificadas 2'), findsOneWidget);
      expect(find.text('No planificadas 1'), findsOneWidget);
      await tester.tap(find.text('No planificadas 1'));
      await tester.pumpAndSettle();
      expect(find.text('Atender incidente'), findsOneWidget);
      expect(find.text('Revisar propuesta'), findsNothing);
      await tester.tap(find.text('Planificadas 2'));
      await tester.pumpAndSettle();
      expect(find.text('Atender incidente'), findsNothing);
      expect(find.text('Revisar propuesta'), findsOneWidget);
      await tester.tap(find.text('Todas 3'));
      await tester.pumpAndSettle();
      expect(find.text('Atender incidente'), findsOneWidget);
      expect(find.text('Revisar propuesta'), findsOneWidget);
    });

    testWidgets('a filter with nothing in it says so, and the filter goes back to "Todas" when the day changes', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Solo planificada');
      await pumpLogbook(tester, repo);
      await tester.tap(find.text('No planificadas 0'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('logbook-filter-empty')), findsOneWidget);
      await tester.tap(find.byKey(const Key('date-previous')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('date-next')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('logbook-filter-empty')), findsNothing);
      expect(find.text('Solo planificada'), findsOneWidget);
    });

    testWidgets('a day without activities has no filter at all', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'x');
      repo.days[formatDate(today)] = LogbookDay(logbook: repo.days[formatDate(today)]!.logbook, plannings: const [], activities: const []);
      await pumpLogbook(tester, repo);
      expect(find.textContaining('Todas '), findsNothing);
      expect(find.text('No hay actividades para esta selección.'), findsOneWidget);
    });
  });

  group('layout', () {
    testWidgets('desktop: the closing, the summary and the audit are a column beside the activities', (tester) async {
      await pumpLogbook(tester, mixedDay());
      final activities = at(tester, find.byKey(const Key('activities-heading')));
      final closure = at(tester, find.byKey(const Key('closure-panel')));
      final summary = at(tester, find.byKey(const Key('summary-section')));
      final audit = at(tester, find.byKey(const Key('logbook-audit')));
      expect(closure.dx, greaterThan(activities.dx));
      expect(summary.dx, closure.dx);
      expect(closure.dy, lessThan(summary.dy));
      expect(summary.dy, lessThan(audit.dy));
      expect(tester.takeException(), isNull);
    });

    for (final size in [tablet, mobile]) {
      testWidgets('${size.width.toInt()} px: activities, then summary, then closing, then audit, with no overflow', (tester) async {
        await pumpLogbook(tester, mixedDay(), size: size);
        for (final key in ['summary-section', 'closure-panel', 'logbook-audit']) {
          await tester.ensureVisible(find.byKey(Key(key)));
        }
        await tester.pumpAndSettle();
        final activities = tester.getTopLeft(find.byKey(const Key('activities-heading'))).dy;
        expect(tester.takeException(), isNull);
        // positions are compared in the scrolled content: the order in the tree is the order on the page
        final order = [for (final k in ['activities-heading', 'summary-section', 'closure-panel', 'logbook-audit']) tester.getTopLeft(find.byKey(Key(k))).dy];
        expect(order[0], lessThan(activities + 1));
        expect(order[1], lessThan(order[2]));
        expect(order[2], lessThan(order[3]));
      });
    }

    testWidgets('the filter wraps on a phone instead of overflowing, with a larger text size too', (tester) async {
      tester.platformDispatcher.textScaleFactorTestValue = 1.5;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await pumpLogbook(tester, mixedDay(), size: mobile);
      expect(tester.takeException(), isNull);
      expect(find.text('No planificadas 1'), findsOneWidget);
    });
  });
}
