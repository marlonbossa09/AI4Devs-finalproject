import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/core/widgets/buttons.dart';
import 'package:smartwork/core/widgets/stat_card.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final yesterday = DateTime.utc(2026, 11, 5);

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
  // On a narrow screen the navigation lives in a menu that has to be opened first
  if (key.startsWith('nav-') && find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

/// One pending activity planned on [date] (origin day), with no progress.
({FakeLogbookRepository repo, Activity activity}) planned({DateTime? date, String title = 'Preparar informe'}) {
  final day = date ?? today;
  final repo = FakeLogbookRepository()..seed(day, title, description: 'Revisar cifras');
  return (repo: repo, activity: repo.days[formatDate(day)]!.activities.single);
}

/// The detail of an activity that is still in the operational list.
Future<void> openDetail(WidgetTester tester, Activity activity) async {
  await tapKey(tester, 'nav-activities');
  await tapKey(tester, 'activity-row-${activity.id}');
}

/// The detail of an activity from the logbook of its origin day (the only place a marked one is listed).
Future<void> openDetailFromLogbook(WidgetTester tester, Activity activity) async {
  containerOf(tester).read(selectedDateProvider.notifier).select(activity.date);
  await tapKey(tester, 'nav-logbook');
  await tapKey(tester, 'activity-open-${activity.id}');
}

Future<void> typeReason(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(const Key('mark-reason')), text);
  await tester.pump();
}

Future<void> openMarkDialog(WidgetTester tester) => tapKey(tester, 'detail-mark-error');

void main() {
  setUpAll(loadTestFonts);

  group('the action in the detail', () {
    testWidgets('is offered on an activity with no progress after its origin day', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      expect(find.byKey(const Key('detail-mark-error')), findsOneWidget);
      expect(find.text('Marcar como registrada por error'), findsOneWidget);
      expect(find.byKey(const Key('detail-revert-mark')), findsNothing);
    });

    testWidgets('progress on the origin day does not take it away', (tester) async {
      final s = planned();
      await s.repo.registerProgress(
        activityId: s.activity.id,
        date: today,
        status: ActivityStatus.inProgress,
        description: 'Primer avance',
        key: 'seed-1',
      );
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      expect(find.byKey(const Key('detail-mark-error')), findsOneWidget);
    });

    testWidgets('progress on a LATER day takes it away: the rule is shown, not offered and refused', (tester) async {
      final s = planned(date: yesterday);
      await s.repo.registerProgress(
        activityId: s.activity.id,
        date: today,
        status: ActivityStatus.inProgress,
        description: 'Seguí hoy',
        key: 'seed-2',
      );
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      expect(find.byKey(const Key('detail-mark-error')), findsNothing);
      expect(find.byKey(const Key('detail-revert-mark')), findsNothing);
    });

    testWidgets('a marked activity offers to revert, not to mark again, and is identified as marked', (tester) async {
      final s = planned();
      s.repo.markAsError(s.activity.id, reason: 'Duplicada');
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.repo.days[formatDate(today)]!.activities.single);
      expect(find.byKey(const Key('detail-revert-mark')), findsOneWidget);
      expect(find.text('Revertir marca'), findsOneWidget);
      expect(find.byKey(const Key('detail-mark-error')), findsNothing);
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
      expect(find.byKey(const Key('detail-marked-tag')), findsOneWidget);
      expect(find.text('REGISTRADA POR ERROR'), findsWidgets);
      expect(find.byKey(const Key('detail-marked-reason')), findsOneWidget);
      expect(find.text('Motivo: Duplicada'), findsOneWidget);
    });

    testWidgets('a marked activity takes no progress, no continuation and no reactivation', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Hecha', status: ActivityStatus.completed);
      final activity = repo.days[formatDate(today)]!.activities.single;
      repo.markAsError(activity.id);
      await pumpApp(tester, logbook: repo);
      await openDetailFromLogbook(tester, activity);
      expect(tester.widget<FilledButton>(find.descendant(
        of: find.byKey(const Key('detail-register-progress')),
        matching: find.byType(FilledButton),
      )).onPressed, isNull);
      expect(find.byKey(const Key('detail-plan-continuation')), findsNothing);
      expect(find.byKey(const Key('detail-reactivate')), findsNothing);
    });

    testWidgets('the history of a marked activity is still there: planning and progress are not hidden', (tester) async {
      final s = planned();
      await s.repo.registerProgress(
        activityId: s.activity.id,
        date: today,
        status: ActivityStatus.inProgress,
        description: 'Avance que se conserva',
        key: 'seed-3',
      );
      s.repo.markAsError(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
      expect(find.text('Avance que se conserva'), findsOneWidget);
      expect(find.text('Preparar informe'), findsWidgets);
    });
  });

  group('marking', () {
    testWidgets('the dialog explains the effect, asks for a mandatory reason and sends nothing yet', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      expect(find.byKey(const Key('mark-title')), findsOneWidget);
      expect(find.byKey(const Key('mark-reason')), findsOneWidget);
      expect(find.textContaining('su historial se conserva'), findsOneWidget);
      expect(find.textContaining('Preparar informe'), findsWidgets);
      expect(s.repo.markRequests, isEmpty);
    });

    testWidgets('an empty or blank reason is not sent and says what is missing', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      for (final text in ['', '   ']) {
        await typeReason(tester, text);
        await tapKey(tester, 'mark-submit');
        expect(find.text('Indica el motivo por el que se registró por error.'), findsOneWidget, reason: '"$text"');
        expect(find.byKey(const Key('mark-title')), findsOneWidget);
      }
      expect(s.repo.markRequests, isEmpty);
    });

    testWidgets('cancelling sends nothing and leaves the activity as it was', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-cancel');
      expect(find.byKey(const Key('mark-title')), findsNothing);
      expect(s.repo.markRequests, isEmpty);
      expect(find.byKey(const Key('detail-mark-error')), findsOneWidget);
    });

    testWidgets('a valid mark is sent once with the trimmed reason and a key; the screen shows what persisted', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, '  Se creó dos veces  ');
      await tapKey(tester, 'mark-submit');

      final sent = s.repo.markRequests.single;
      expect(sent['activityId'], s.activity.id);
      expect(sent['reason'], 'Se creó dos veces');
      expect((sent['key'] as String).length, 32);
      expect(find.byKey(const Key('mark-title')), findsNothing);
      expect(find.text('Actividad marcada como registrada por error.'), findsOneWidget);
      // The detail is reloaded from the server: it now says it is marked and offers the way back
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
      expect(find.text('Motivo: Se creó dos veces'), findsOneWidget);
      expect(find.byKey(const Key('detail-revert-mark')), findsOneWidget);
      expect(find.byKey(const Key('detail-mark-error')), findsNothing);
      // Nothing was deleted: the activity and its planning are still there
      expect(s.repo.days[formatDate(today)]!.activities.length, 1);
      expect(s.repo.days[formatDate(today)]!.plannings.length, 1);
      expect(s.repo.days[formatDate(today)]!.activities.single.status, ActivityStatus.pending);
    });

    testWidgets('the server refusing for later progress is explained in the dialog, which stays open', (tester) async {
      final s = planned();
      s.repo.markErrors.add(const ApiError(code: 'MARCA_NO_PROCEDE', message: 'x', status: 409));
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-submit');
      expect(find.byKey(const Key('mark-error')), findsOneWidget);
      expect(find.textContaining('avances en jornadas posteriores'), findsOneWidget);
      expect(find.byKey(const Key('mark-title')), findsOneWidget);
      await tapKey(tester, 'mark-cancel');
      expect(s.repo.days[formatDate(today)]!.activities.single.marked, isFalse); // nothing was marked
    });

    testWidgets('a refusal because a closed day would lose its only valid activity says how to proceed', (tester) async {
      final s = planned();
      s.repo.closeDay(today);
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-submit');
      expect(find.textContaining('Reabre esa jornada'), findsOneWidget);
      expect(find.byKey(const Key('mark-title')), findsOneWidget);
      // Nothing changed
      expect(s.repo.days[formatDate(today)]!.activities.single.marked, isFalse);
      expect(s.repo.days[formatDate(today)]!.logbook.closed, isTrue);
    });

    testWidgets('a closed day with ANOTHER valid activity accepts the mark and stays closed, with no reopening', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'Una', description: 'a')
        ..seed(today, 'Dos', description: 'b');
      final first = repo.days[formatDate(today)]!.activities.first;
      repo.closeDay(today);
      await pumpApp(tester, logbook: repo);
      await openDetail(tester, first);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-submit');
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
      expect(repo.days[formatDate(today)]!.logbook.closed, isTrue);
      expect(repo.calls.where((c) => c.startsWith('reopen')), isEmpty);
    });

    testWidgets('a second tap while the request runs sends nothing, the dialog cannot be closed and shows it is working', (tester) async {
      final s = planned();
      s.repo.markGate = Completer<void>();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      final submit = find.byKey(const Key('mark-submit'));
      await tester.tap(submit);
      await tester.pump();
      await tester.tap(submit, warnIfMissed: false);
      await tester.tap(submit, warnIfMissed: false);
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(s.repo.markRequests.length, 1);
      // Cancelling is disabled while the request runs
      expect(tester.widget<SecondaryButton>(find.byKey(const Key('mark-cancel'))).onPressed, isNull);
      expect(find.byKey(const Key('mark-title')), findsOneWidget);

      s.repo.markGate!.complete();
      await tester.pumpAndSettle();
      expect(s.repo.markRequests.length, 1);
      expect(s.repo.days[formatDate(today)]!.activities.single.marked, isTrue);
    });

    testWidgets('retrying the SAME mark after a failure reuses the key; changing the reason gets a new one', (tester) async {
      final s = planned();
      s.repo.markErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-submit');
      expect(find.byKey(const Key('mark-error')), findsOneWidget);
      await tapKey(tester, 'mark-submit');
      final keys = s.repo.markRequests.map((r) => r['key']).toList();
      expect(keys.length, 2);
      expect(keys[0], keys[1]); // same intention: same key, so the server never repeats the effect
      expect(s.repo.days[formatDate(today)]!.activities.single.marked, isTrue);
    });

    testWidgets('a different reason after a failure is a different intention with a new key', (tester) async {
      final s = planned();
      s.repo.markErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Primer motivo');
      await tapKey(tester, 'mark-submit');
      await typeReason(tester, 'Otro motivo');
      await tapKey(tester, 'mark-submit');
      final keys = s.repo.markRequests.map((r) => r['key']).toList();
      expect(keys[0], isNot(keys[1]));
    });
  });

  group('after marking, the activity leaves the operational views and stays consultable', () {
    testWidgets('it leaves the activity list but the logbook of its day lists it apart, with its reason', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-submit');

      await tapKey(tester, 'nav-activities');
      expect(find.byKey(Key('activity-row-${s.activity.id}')), findsNothing);

      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(const Key('marked-heading')), findsOneWidget);
      expect(find.text('REGISTRADAS POR ERROR (1)'), findsOneWidget);
      expect(find.byKey(Key('marked-tag-${s.activity.id}')), findsOneWidget);
      expect(find.byKey(Key('marked-reason-${s.activity.id}')), findsOneWidget);
      // No action that records work on it
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsNothing);
      expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsNothing);
      expect(find.byKey(Key('reactivation-action-${s.activity.id}')), findsNothing);
      expect(find.byKey(Key('activity-open-${s.activity.id}')), findsOneWidget);
    });

    testWidgets('the dashboard counts and lists leave it out', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'Se queda')
        ..seed(today, 'Hecha', status: ActivityStatus.completed);
      final done = repo.days[formatDate(today)]!.activities.last;
      repo.markAsError(done.id);
      await pumpApp(tester, logbook: repo);
      expect(stat(tester, 'Actividades registradas').value, 1);
      expect(stat(tester, 'Completadas').value, 0);
      expect(find.text('Hecha'), findsNothing);
      expect(find.text('Se queda'), findsWidgets);
    });

    testWidgets('marking from the detail refreshes the dashboard counts', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'Una')
        ..seed(today, 'Dos');
      final first = repo.days[formatDate(today)]!.activities.first;
      await pumpApp(tester, logbook: repo);
      expect(stat(tester, 'Actividades registradas').value, 2);
      await openDetail(tester, first);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      await tapKey(tester, 'mark-submit');
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Actividades registradas').value, 1);
      expect(stat(tester, 'Pendientes').value, 1);
    });
  });

  group('reverting', () {
    Future<({FakeLogbookRepository repo, Activity activity})> marked() async {
      final s = planned();
      s.repo.markAsError(s.activity.id, reason: 'Duplicada');
      return (repo: s.repo, activity: s.repo.days[formatDate(today)]!.activities.single);
    }

    testWidgets('asks for a confirmation, with no reason, and sends nothing yet', (tester) async {
      final s = await marked();
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      await tapKey(tester, 'detail-revert-mark');
      expect(find.byKey(const Key('revert-title')), findsOneWidget);
      expect(find.byType(TextField), findsNothing); // no reason is asked
      expect(s.repo.markRequests, isEmpty);
      await tapKey(tester, 'revert-cancel');
      expect(find.byKey(const Key('revert-title')), findsNothing);
      expect(s.repo.markRequests, isEmpty);
      expect(find.byKey(const Key('detail-revert-mark')), findsOneWidget);
    });

    testWidgets('confirming reverts it: the activity is back in the list, the logbook and the counts', (tester) async {
      final s = await marked();
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      await tapKey(tester, 'detail-revert-mark');
      await tapKey(tester, 'revert-submit');

      final sent = s.repo.markRequests.single;
      expect(sent['activityId'], s.activity.id);
      expect(sent.containsKey('reason'), isFalse);
      expect((sent['key'] as String).length, 32);
      expect(find.text('Marca de error revertida.'), findsOneWidget);
      expect(find.byKey(const Key('detail-marked')), findsNothing);
      expect(find.byKey(const Key('detail-mark-error')), findsOneWidget);

      await tapKey(tester, 'nav-activities');
      expect(find.byKey(Key('activity-row-${s.activity.id}')), findsOneWidget);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(const Key('marked-heading')), findsNothing);
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsOneWidget);
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Actividades registradas').value, 1);
    });

    testWidgets('a mark that is no longer in force is explained and the screen is refreshed', (tester) async {
      final s = await marked();
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      expect(find.byKey(const Key('detail-revert-mark')), findsOneWidget);
      s.repo.clearMarkBehindTheScreen(s.activity.id); // reverted from elsewhere: the screen is stale
      await tapKey(tester, 'detail-revert-mark');
      await tapKey(tester, 'revert-submit');
      expect(find.byKey(const Key('revert-error')), findsOneWidget);
      expect(find.textContaining('ya no tiene una marca'), findsOneWidget);
      expect(find.byKey(const Key('revert-title')), findsOneWidget);
      await tapKey(tester, 'revert-cancel');
      // The screen was refreshed from the server: it no longer offers to revert, it offers to mark
      expect(find.byKey(const Key('detail-revert-mark')), findsNothing);
      expect(find.byKey(const Key('detail-mark-error')), findsOneWidget);
      expect(find.byKey(const Key('detail-marked')), findsNothing);
    });

    testWidgets('retrying the SAME reversion after a failure reuses the key', (tester) async {
      final s = await marked();
      s.repo.markErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      await tapKey(tester, 'detail-revert-mark');
      await tapKey(tester, 'revert-submit');
      expect(find.byKey(const Key('revert-error')), findsOneWidget);
      await tapKey(tester, 'revert-submit');
      final keys = s.repo.markRequests.map((r) => r['key']).toList();
      expect(keys.length, 2);
      expect(keys[0], keys[1]);
      expect(s.repo.days[formatDate(today)]!.activities.single.marked, isFalse);
    });

    testWidgets('while the detail reloads after a mark it keeps showing the activity, not a loader', (tester) async {
      final s = planned();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openMarkDialog(tester);
      await typeReason(tester, 'Duplicada');
      s.repo.detailGate = Completer<void>(); // the reload of the detail is held back
      await tester.tap(find.byKey(const Key('mark-submit')));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
      expect(find.byKey(const Key('detail-loading')), findsNothing);
      expect(find.byKey(const Key('detail-register-progress')), findsOneWidget);
      s.repo.detailGate!.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
    });

    testWidgets('a second tap while the request runs sends nothing', (tester) async {
      final s = await marked();
      s.repo.markGate = Completer<void>();
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      await tapKey(tester, 'detail-revert-mark');
      final submit = find.byKey(const Key('revert-submit'));
      await tester.tap(submit);
      await tester.pump();
      await tester.tap(submit, warnIfMissed: false);
      await tester.tap(submit, warnIfMissed: false);
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(s.repo.markRequests.length, 1);
      s.repo.markGate!.complete();
      await tester.pumpAndSettle();
      expect(s.repo.markRequests.length, 1);
    });

    testWidgets('after reverting, it can be marked again (a new cycle)', (tester) async {
      final s = await marked();
      await pumpApp(tester, logbook: s.repo);
      await openDetailFromLogbook(tester, s.activity);
      await tapKey(tester, 'detail-revert-mark');
      await tapKey(tester, 'revert-submit');
      await openMarkDialog(tester);
      await typeReason(tester, 'Otra vez');
      await tapKey(tester, 'mark-submit');
      expect(find.text('Motivo: Otra vez'), findsOneWidget);
      expect(s.repo.markRequests.length, 2);
      expect(s.repo.markRequests[0]['key'], isNot(s.repo.markRequests[1]['key']));
    });
  });

  group('every screen size', () {
    for (final entry in {'mobile': mobile, 'tablet': tablet, 'desktop': desktop}.entries) {
      testWidgets('${entry.key}: mark and revert work with the dialog fully usable', (tester) async {
        final s = planned();
        await pumpApp(tester, logbook: s.repo, size: entry.value);
        await openDetail(tester, s.activity);
        await openMarkDialog(tester);
        expect(tester.takeException(), isNull);
        await typeReason(tester, 'Duplicada');
        await tapKey(tester, 'mark-submit');
        expect(find.byKey(const Key('detail-marked')), findsOneWidget);
        await tapKey(tester, 'detail-revert-mark');
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'revert-submit');
        expect(find.byKey(const Key('detail-mark-error')), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
