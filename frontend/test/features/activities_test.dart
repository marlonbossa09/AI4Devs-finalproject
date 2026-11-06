import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/activity_detail.dart';
import 'package:smartwork/features/logbook/presentation/providers/activity_list.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_notifier.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final yesterday = DateTime.utc(2026, 11, 5);
final twoDaysAgo = DateTime.utc(2026, 11, 4);

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

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Opens the activity list from the sidebar. On mobile the sidebar is a drawer opened from the
/// top bar, so it is opened first.
Future<void> openList(WidgetTester tester) async {
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
  await tapKey(tester, 'nav-activities');
}

Future<void> openDetail(WidgetTester tester, Activity activity) => tapKey(tester, 'activity-row-${activity.id}');

Activity activityOf(FakeLogbookRepository repo, String title) {
  for (final day in repo.days.values) {
    for (final activity in day.activities) {
      if (activity.title == title) return activity;
    }
  }
  throw StateError('No activity "$title"');
}

/// The ids of the list rows, in the order they are shown.
List<String> rowIds(WidgetTester tester) => [
  for (final widget in tester.widgetList(find.byWidgetPredicate(
    (w) => w.key is ValueKey<String> && (w.key as ValueKey<String>).value.startsWith('activity-row-'),
  )))
    (widget.key as ValueKey<String>).value.substring('activity-row-'.length),
];

Future<void> record(
  FakeLogbookRepository repo,
  Activity activity,
  DateTime date,
  ActivityStatus status,
  String description, {
  String? reason,
}) => repo.registerProgress(
  activityId: activity.id,
  date: date,
  status: status,
  description: description,
  blockReason: reason,
  key: 'k-${repo.progressRequests.length}',
);

Finder pill(String key, String label) => find.descendant(of: find.byKey(Key(key)), matching: find.text(label));

void main() {
  setUpAll(loadTestFonts);

  group('the activity list (M2-08)', () {
    testWidgets('is reached from the sidebar and shows every activity, newest first, with its origin and status', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(twoDaysAgo, 'La más antigua')
        ..seed(yesterday, 'La del medio', status: ActivityStatus.inProgress)
        ..seed(today, 'La más reciente', status: ActivityStatus.completed);
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      expect(find.text('Mis actividades'), findsWidgets);
      final titles = [for (final id in rowIds(tester)) id];
      expect(titles, [
        activityOf(repo, 'La más reciente').id,
        activityOf(repo, 'La del medio').id,
        activityOf(repo, 'La más antigua').id,
      ]);
      // From any day, not only the one selected
      expect(find.text('La más antigua'), findsOneWidget);
      expect(pill('row-status-${activityOf(repo, 'La del medio').id}', 'En progreso'), findsOneWidget);
      expect(pill('row-status-${activityOf(repo, 'La más reciente').id}', 'Completada'), findsOneWidget);
      expect(find.text('Actividad planificada'), findsNWidgets(3));
      // It asks the server, with no filter and no cursor
      expect(repo.listRequests.single, {'statuses': <ActivityStatus>[], 'limit': null, 'cursor': null});
    });

    testWidgets('shows a loading state while the server answers', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      repo.listGate = Completer<void>();
      await pumpApp(tester, logbook: repo);
      await tester.tap(find.byKey(const Key('nav-activities')));
      await tester.pump();
      await tester.pump();
      expect(find.byKey(const Key('activities-loading')), findsOneWidget);
      expect(find.text('Preparar informe'), findsNothing);
      repo.listGate!.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('activities-loading')), findsNothing);
      expect(find.text('Preparar informe'), findsOneWidget);
    });

    testWidgets('shows an empty state when there are no activities', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openList(tester);
      expect(find.byKey(const Key('activities-empty')), findsOneWidget);
      expect(find.textContaining('Todavía no tienes actividades'), findsOneWidget);
      expect(find.byKey(const Key('activities-load-more')), findsNothing);
    });

    testWidgets('shows an error with a retry when the list cannot be loaded', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      repo.listErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      expect(find.text('Preparar informe'), findsNothing);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.textContaining('No se pudo conectar'), findsNothing);
      expect(find.text('Preparar informe'), findsOneWidget);
    });

    testWidgets('does not list the activities marked as registered by mistake (CA-119)', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'Visible')
        ..seed(today, 'Por error');
      repo.markAsError(activityOf(repo, 'Por error').id);
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      expect(find.text('Visible'), findsOneWidget);
      expect(find.text('Por error'), findsNothing);
    });

    group('filter', () {
      FakeLogbookRepository mixed() => FakeLogbookRepository()
        ..seed(today, 'Pendiente 1')
        ..seed(today, 'En progreso 1', status: ActivityStatus.inProgress)
        ..seed(today, 'Bloqueada 1', status: ActivityStatus.blocked)
        ..seed(today, 'Completada 1', status: ActivityStatus.completed);

      testWidgets('offers "Todas" and the four statuses, with "Todas" selected at first', (tester) async {
        await pumpApp(tester, logbook: mixed());
        await openList(tester);
        for (final key in ['all', ...ActivityStatus.values.map((s) => s.name)]) {
          expect(find.byKey(Key('activity-filter-$key')), findsOneWidget, reason: key);
        }
        expect(
          find.descendant(of: find.byKey(const Key('activity-filter-all')), matching: find.byIcon(Icons.check)),
          findsOneWidget,
        );
        expect(rowIds(tester), hasLength(4));
      });

      testWidgets('filters by the current status and asks the server for it', (tester) async {
        final repo = mixed();
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activity-filter-blocked');
        expect(find.text('Bloqueada 1'), findsOneWidget);
        expect(find.text('Pendiente 1'), findsNothing);
        expect(find.text('Completada 1'), findsNothing);
        expect(repo.listRequests.last['statuses'], [ActivityStatus.blocked]);
        expect(repo.listRequests.last['cursor'], isNull);
      });

      testWidgets('accepts several statuses at once and "Todas" clears them', (tester) async {
        final repo = mixed();
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activity-filter-pending');
        await tapKey(tester, 'activity-filter-completed');
        expect(rowIds(tester), hasLength(2));
        expect(find.text('Pendiente 1'), findsOneWidget);
        expect(find.text('Completada 1'), findsOneWidget);
        expect(repo.listRequests.last['statuses'], [ActivityStatus.pending, ActivityStatus.completed]);
        await tapKey(tester, 'activity-filter-all');
        expect(rowIds(tester), hasLength(4));
        expect(repo.listRequests.last['statuses'], isEmpty);
      });

      testWidgets('tapping a selected status again removes it', (tester) async {
        final repo = mixed();
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activity-filter-pending');
        await tapKey(tester, 'activity-filter-pending');
        expect(rowIds(tester), hasLength(4));
        expect(repo.listRequests.last['statuses'], isEmpty);
      });

      testWidgets('a filter without results is an empty list, not an error', (tester) async {
        final repo = FakeLogbookRepository()..seed(today, 'Solo pendiente');
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activity-filter-completed');
        expect(find.text('No hay actividades con este filtro.'), findsOneWidget);
        expect(find.byKey(const Key('load-error')), findsNothing);
      });

      testWidgets('is kept when going to a detail and back', (tester) async {
        final repo = mixed();
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activity-filter-blocked');
        await openDetail(tester, activityOf(repo, 'Bloqueada 1'));
        await tapKey(tester, 'detail-back');
        expect(rowIds(tester), [activityOf(repo, 'Bloqueada 1').id]);
        expect(repo.listRequests.last['statuses'], [ActivityStatus.blocked]);
      });
    });

    group('pagination', () {
      FakeLogbookRepository many(int count, {int pageSize = 20}) {
        final repo = FakeLogbookRepository()..defaultPageSize = pageSize;
        for (var i = 1; i <= count; i++) {
          repo.seed(today, 'Actividad $i');
        }
        return repo;
      }

      testWidgets('loads the first page and offers to load more, with the cursor of the contract', (tester) async {
        final repo = many(25);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        expect(rowIds(tester), hasLength(20));
        expect(find.byKey(const Key('activities-load-more')), findsOneWidget);
        expect(find.textContaining('20 actividades cargadas · hay más'), findsOneWidget);
        final lastShown = rowIds(tester).last;

        await tapKey(tester, 'activities-load-more');
        expect(repo.listRequests.last['cursor'], lastShown); // the server gave it; the client only returns it
        expect(rowIds(tester), hasLength(25));
        expect(rowIds(tester).toSet(), hasLength(25)); // none repeated
        expect(find.byKey(const Key('activities-load-more')), findsNothing); // no more pages
        expect(find.textContaining('25 actividades cargadas'), findsOneWidget);
        expect(find.textContaining('hay más'), findsNothing);
      });

      testWidgets('walks every page in order without repeating or skipping', (tester) async {
        final repo = many(7, pageSize: 3);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        while (find.byKey(const Key('activities-load-more')).evaluate().isNotEmpty) {
          await tapKey(tester, 'activities-load-more');
        }
        final expected = [for (var i = 7; i >= 1; i--) activityOf(repo, 'Actividad $i').id];
        expect(rowIds(tester), expected);
        expect(repo.listRequests.length, 3); // 3 + 3 + 1
      });

      testWidgets('shows a loading state on the button while the next page loads and blocks a second request', (tester) async {
        final repo = many(5, pageSize: 2);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        repo.listGate = Completer<void>();
        await tester.ensureVisible(find.byKey(const Key('activities-load-more')));
        await tester.tap(find.byKey(const Key('activities-load-more')));
        await tester.pump();
        expect(find.text('Cargando…'), findsOneWidget);
        await tester.tap(find.byKey(const Key('activities-load-more')), warnIfMissed: false);
        await tester.pump();
        expect(repo.listRequests.length, 2); // first page + exactly one "load more"
        repo.listGate!.complete();
        await tester.pumpAndSettle();
        expect(rowIds(tester), hasLength(4));
      });

      testWidgets('a failed page keeps what is shown and can be retried', (tester) async {
        final repo = many(5, pageSize: 2);
        repo.listErrors.addAll([null, const ApiError(code: ApiError.network, message: 'x')]);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activities-load-more');
        expect(rowIds(tester), hasLength(2)); // nothing lost
        expect(find.byKey(const Key('activities-more-error')), findsOneWidget);
        expect(find.text('Reintentar'), findsOneWidget);
        await tapKey(tester, 'activities-load-more');
        expect(find.byKey(const Key('activities-more-error')), findsNothing);
        expect(rowIds(tester), hasLength(4));
        expect(rowIds(tester).toSet(), hasLength(4));
      });

      testWidgets('changing the filter starts again from the first page', (tester) async {
        final repo = many(5, pageSize: 2);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        await tapKey(tester, 'activities-load-more');
        expect(repo.listRequests.last['cursor'], isNotNull);
        await tapKey(tester, 'activity-filter-pending');
        expect(repo.listRequests.last['cursor'], isNull);
        expect(rowIds(tester), hasLength(2));
      });

      testWidgets('a stale page that arrives AFTER the filtered list is discarded', (tester) async {
        final repo = FakeLogbookRepository()..defaultPageSize = 2;
        for (var i = 1; i <= 3; i++) {
          repo.seed(today, 'Pendiente $i');
        }
        repo.seed(today, 'Hecha', status: ActivityStatus.completed);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        final loadMore = Completer<void>();
        final filtered = Completer<void>();
        repo.listGates.addAll([loadMore, filtered]); // 1st call = load more, 2nd = the new filter
        await tester.ensureVisible(find.byKey(const Key('activities-load-more')));
        await tester.tap(find.byKey(const Key('activities-load-more')));
        await tester.pump();
        await tester.ensureVisible(find.byKey(const Key('activity-filter-completed')));
        await tester.tap(find.byKey(const Key('activity-filter-completed')));
        await tester.pump();
        filtered.complete(); // the filtered list arrives first...
        await tester.pumpAndSettle();
        expect(rowIds(tester), [activityOf(repo, 'Hecha').id]);
        loadMore.complete(); // ...and then the old page, which must not be appended
        await tester.pumpAndSettle();
        expect(rowIds(tester), [activityOf(repo, 'Hecha').id]);
        expect(find.byKey(const Key('activities-load-more')), findsNothing);
      });

      testWidgets('a page that arrives after the filter changed is discarded', (tester) async {
        final repo = FakeLogbookRepository()..defaultPageSize = 2;
        for (var i = 1; i <= 3; i++) {
          repo.seed(today, 'Pendiente $i');
        }
        repo.seed(today, 'Hecha', status: ActivityStatus.completed);
        await pumpApp(tester, logbook: repo);
        await openList(tester);
        repo.listGate = Completer<void>();
        await tester.ensureVisible(find.byKey(const Key('activities-load-more')));
        await tester.tap(find.byKey(const Key('activities-load-more'))); // in flight, unfiltered
        await tester.pump();
        await tester.ensureVisible(find.byKey(const Key('activity-filter-completed')));
        await tester.tap(find.byKey(const Key('activity-filter-completed'))); // the filter changes meanwhile
        await tester.pump();
        repo.listGate!.complete();
        await tester.pumpAndSettle();
        expect(rowIds(tester), [activityOf(repo, 'Hecha').id]); // only the filtered list, no leftovers
      });
    });
  });

  group('data refresh', () {
    test('recording progress reloads a detail and a list that are still being watched', () async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      final container = ProviderContainer(
        retry: noAutomaticRetry,
        overrides: [logbookRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      final detail = container.listen(activityDetailProvider(activity.id), (previous, next) {});
      final list = container.listen(activityListProvider, (previous, next) {});
      await container.read(activityDetailProvider(activity.id).future);
      await container.read(activityListProvider.future);
      expect(detail.read().requireValue.status, ActivityStatus.pending);
      expect(list.read().requireValue.items.single.status, ActivityStatus.pending);

      await container.read(logbookProvider(today).notifier).registerProgress(
        activityId: activity.id,
        status: ActivityStatus.inProgress,
        description: 'Empecé',
        key: 'k-1',
      );
      await container.read(activityDetailProvider(activity.id).future);
      await container.read(activityListProvider.future);

      expect(detail.read().requireValue.status, ActivityStatus.inProgress);
      expect(detail.read().requireValue.progress.single.description, 'Empecé');
      expect(list.read().requireValue.items.single.status, ActivityStatus.inProgress);
      expect(repo.detailRequests.length, 2); // reloaded from the API, not patched on the client
    });
  });

  group('the activity detail (M2-07)', () {
    testWidgets('opens from a list row and shows the title, the current status and the dates', (tester) async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'Preparar informe', description: 'Revisar cifras');
      final activity = activityOf(repo, 'Preparar informe');
      await record(repo, activity, today, ActivityStatus.inProgress, 'Empecé');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activity);
      expect(find.text('Preparar informe'), findsWidgets);
      expect(find.text('DETALLE DE ACTIVIDAD'), findsOneWidget);
      expect(pill('detail-status', 'En progreso'), findsOneWidget);
      expect(find.text('Actividad planificada'), findsOneWidget);
      expect(tester.widget<Text>(find.byKey(const Key('detail-origin-date'))).data, formatShortDate(yesterday));
      expect(repo.detailRequests, [activity.id]);
    });

    testWidgets('keeps what was planned apart from what was done, each with its own heading', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
      final activity = activityOf(repo, 'Preparar informe');
      await record(repo, activity, today, ActivityStatus.inProgress, 'Avancé con el informe');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activity);
      expect(find.text('PLANIFICACIÓN'), findsOneWidget);
      expect(find.text('EJECUCIÓN'), findsOneWidget);
      expect(find.text('Lo planificado'), findsOneWidget);
      expect(find.text('Historial de avances'), findsOneWidget);
      final planned = find.byKey(const Key('detail-planning-original'));
      expect(find.descendant(of: planned, matching: find.text('Revisar cifras')), findsOneWidget);
      expect(find.descendant(of: planned, matching: find.text('Avancé con el informe')), findsNothing);
      final done = find.byKey(Key('detail-progress-${repo.progressStored(activity.id).single.id}'));
      expect(find.descendant(of: done, matching: find.text('Avancé con el informe')), findsOneWidget);
      expect(find.descendant(of: done, matching: find.text('Revisar cifras')), findsNothing);
      expect(find.text('Lo previsto. No es un avance'), findsNothing);
      expect(find.textContaining('No es un avance y no cambia el estado'), findsOneWidget);
    });

    testWidgets('lists the progress in sequence order with the work date and the status each had', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      // Recorded out of order: the work date decides the order, not the moment of registration
      await record(repo, activity, today, ActivityStatus.blocked, 'Hoy', reason: 'Falta el acceso');
      await record(repo, activity, twoDaysAgo, ActivityStatus.pending, 'Hace dos días');
      await record(repo, activity, yesterday, ActivityStatus.inProgress, 'Ayer');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activity);
      final stored = repo.progressStored(activity.id);
      expect([for (final p in stored) formatShortDate(p.date)], [
        formatShortDate(twoDaysAgo),
        formatShortDate(yesterday),
        formatShortDate(today),
      ]);
      // On screen, in that same order (top to bottom)
      final tops = [
        for (final p in stored) tester.getTopLeft(find.byKey(Key('detail-progress-${p.id}'))).dy,
      ];
      expect(tops, orderedEquals([...tops]..sort()));
      expect([for (final p in stored) tester.widget<Text>(find.byKey(Key('detail-progress-date-${p.id}'))).data], [
        formatShortDate(twoDaysAgo),
        formatShortDate(yesterday),
        formatShortDate(today),
      ]);
      // Each keeps the status it had, and the old block reason still shows
      expect(pill('detail-progress-status-${stored[0].id}', 'Pendiente'), findsOneWidget);
      expect(pill('detail-progress-status-${stored[1].id}', 'En progreso'), findsOneWidget);
      expect(pill('detail-progress-status-${stored[2].id}', 'Bloqueada'), findsOneWidget);
      expect(find.text('Motivo del bloqueo: Falta el acceso'), findsOneWidget);
      expect(find.text('Fecha laboral'), findsNWidgets(3));
      expect(pill('detail-status', 'Bloqueada'), findsOneWidget); // current = the last of the sequence
    });

    testWidgets('a retroactive entry does not replace the current status', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      await record(repo, activity, yesterday, ActivityStatus.inProgress, 'Martes');
      await record(repo, activity, twoDaysAgo, ActivityStatus.completed, 'Lunes');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activity);
      expect(pill('detail-status', 'En progreso'), findsOneWidget);
      final ids = [for (final p in repo.progressStored(activity.id)) p.id];
      expect(pill('detail-progress-status-${ids.first}', 'Completada'), findsOneWidget); // historical
    });

    testWidgets('an activity with no progress says so, and is still Pendiente', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activityOf(repo, 'Preparar informe'));
      expect(find.byKey(const Key('detail-no-progress')), findsOneWidget);
      expect(find.text('Todavía no hay avances registrados.'), findsOneWidget);
      expect(pill('detail-status', 'Pendiente'), findsOneWidget);
    });

    testWidgets('planned continuations are shown with the planning, not as progress', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      repo.addContinuation(activity.id, DateTime.utc(2026, 11, 9), 'Seguir el lunes');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activity);
      expect(find.text('Continuación prevista'), findsOneWidget);
      expect(find.text('Seguir el lunes'), findsOneWidget);
      expect(find.text('09/11/2026'), findsOneWidget);
      expect(find.byKey(const Key('detail-no-progress')), findsOneWidget); // still no execution
      expect(pill('detail-status', 'Pendiente'), findsOneWidget);
    });

    testWidgets('an activity marked as a mistake is consultable, says so and cannot take progress', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      await record(repo, activity, today, ActivityStatus.inProgress, 'Algo se hizo');
      repo.markAsError(activity.id, reason: 'Duplicada');
      await pumpApp(tester, logbook: repo);
      // Marked activities are not in the list; the detail is reached from Mi bitácora
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${activity.id}');
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
      expect(find.textContaining('Motivo: Duplicada'), findsOneWidget);
      expect(find.text('Algo se hizo'), findsOneWidget); // the history is kept
      final register = tester.widget<FilledButton>(find.descendant(
        of: find.byKey(const Key('detail-register-progress')),
        matching: find.byType(FilledButton),
      ));
      expect(register.onPressed, isNull);
    });

    testWidgets('shows a loading state, then the detail', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      repo.detailGate = Completer<void>();
      await tester.tap(find.byKey(Key('activity-row-${activityOf(repo, 'Preparar informe').id}')));
      await tester.pump();
      await tester.pump();
      expect(find.byKey(const Key('detail-loading')), findsOneWidget);
      repo.detailGate!.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('detail-loading')), findsNothing);
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
    });

    testWidgets('an unavailable activity is explained without revealing anything, and can be left or retried', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      repo.detailErrors.add(const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404));
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activityOf(repo, 'Preparar informe'));
      expect(find.text('El recurso solicitado no está disponible.'), findsOneWidget);
      expect(find.byKey(const Key('detail-planning-original')), findsNothing);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
    });

    testWidgets('a network failure is reported and can be retried', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      repo.detailErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activityOf(repo, 'Preparar informe'));
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.textContaining('No se pudo conectar'), findsNothing);
    });

    testWidgets('an expired session sends the user back to the login', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      repo.detailErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activityOf(repo, 'Preparar informe'));
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('navigation', () {
    testWidgets('the detail goes back to the list that opened it', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activityOf(repo, 'Preparar informe'));
      expect(find.text('← Mis actividades'), findsOneWidget);
      await tapKey(tester, 'detail-back');
      expect(find.byKey(const Key('activity-filter-all')), findsOneWidget);
    });

    testWidgets('"Ver detalle" in Mi bitácora opens the detail and goes back to Mi bitácora', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${activity.id}');
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
      expect(find.text('← Mi bitácora'), findsOneWidget);
      await tapKey(tester, 'detail-back');
      expect(find.byKey(const Key('logbook-new-planning')), findsOneWidget);
    });

    testWidgets('"Ver detalle" in the dashboard opens the detail and goes back to the dashboard', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await tapKey(tester, 'activity-open-${activity.id}');
      expect(find.text('← Panel principal'), findsOneWidget);
      await tapKey(tester, 'detail-back');
      expect(find.byKey(const Key('dashboard-new-planning')), findsOneWidget);
    });

    testWidgets('"Planificar actividad" in the list goes to the planning form', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openList(tester);
      await tapKey(tester, 'activities-new-planning');
      expect(find.byKey(const Key('plan-submit')), findsOneWidget);
    });

    testWidgets('records progress from the detail even if the activity is from another day, and returns to the detail', (tester) async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'Preparar informe', description: 'Revisar cifras');
      final activity = activityOf(repo, 'Preparar informe');
      await pumpApp(tester, logbook: repo); // the day being looked at is today: the activity is not in it
      await openList(tester);
      await openDetail(tester, activity);
      await tapKey(tester, 'detail-register-progress');
      // The form already has the activity chosen
      expect(find.descendant(of: find.byKey(const Key('progress-activity')), matching: find.text('Preparar informe')), findsOneWidget);
      await tapKey(tester, 'progress-status-inProgress');
      await tester.enterText(find.byKey(const Key('progress-description')), 'Avancé desde el detalle');
      await tapKey(tester, 'progress-submit');
      expect(repo.progressRequests.single['activityId'], activity.id);
      expect(find.text('Avance registrado.'), findsOneWidget);
      // Back in the detail, reloaded from the API: new status and the new entry
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
      expect(pill('detail-status', 'En progreso'), findsOneWidget);
      expect(find.text('Avancé desde el detalle'), findsOneWidget);
      expect(repo.detailRequests.length, 2);
    });

    testWidgets('cancelling the form returns to the detail', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      await openDetail(tester, activity);
      await tapKey(tester, 'detail-register-progress');
      await tapKey(tester, 'progress-cancel');
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
      expect(repo.progressRequests, isEmpty);
    });

    testWidgets('the list shows the new status after recording progress', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Preparar informe');
      final activity = activityOf(repo, 'Preparar informe');
      await pumpApp(tester, logbook: repo);
      await openList(tester);
      expect(pill('row-status-${activity.id}', 'Pendiente'), findsOneWidget);
      await openDetail(tester, activity);
      await tapKey(tester, 'detail-register-progress');
      await tapKey(tester, 'progress-status-completed');
      await tester.enterText(find.byKey(const Key('progress-description')), 'Terminé');
      await tapKey(tester, 'progress-submit');
      await tapKey(tester, 'detail-back');
      expect(pill('row-status-${activity.id}', 'Completada'), findsOneWidget);
    });
  });

  group('responsive', () {
    for (final (name, size) in [('tablet', tablet), ('mobile', mobile)]) {
      testWidgets('the list and the detail work on $name without layout errors', (tester) async {
        final repo = FakeLogbookRepository()..seed(yesterday, 'Preparar informe con un título bastante largo para comprobar el ajuste', description: 'Revisar cifras');
        final activity = activityOf(repo, 'Preparar informe con un título bastante largo para comprobar el ajuste');
        await record(repo, activity, today, ActivityStatus.blocked, 'Me detuve esperando una respuesta que tarda', reason: 'Falta el acceso al servidor');
        repo.addContinuation(activity.id, DateTime.utc(2026, 11, 9), 'Seguir el lunes');
        await pumpApp(tester, logbook: repo, size: size);
        await openList(tester);
        expect(find.byKey(Key('activity-row-${activity.id}')), findsOneWidget);
        await tapKey(tester, 'activity-filter-blocked');
        expect(rowIds(tester), [activity.id]);
        await openDetail(tester, activity);
        expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
        expect(find.byKey(Key('detail-progress-${repo.progressStored(activity.id).single.id}')), findsOneWidget);
        expect(find.text('Motivo del bloqueo: Falta el acceso al servidor'), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'detail-register-progress');
        expect(find.byKey(const Key('progress-submit')), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
