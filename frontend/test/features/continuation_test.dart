import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/core/widgets/stat_card.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/activity_detail.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const mobile = Size(400, 900);

final tomorrow = DateTime.utc(2026, 11, 7);
final nextMonday = DateTime.utc(2026, 11, 9);

Future<void> pumpApp(
  WidgetTester tester, {
  required FakeLogbookRepository logbook,
  Size size = desktop,
}) async {
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

/// Goes to Mi bitácora (on a phone the sidebar is a drawer opened from the top bar).
Future<void> goToLogbook(WidgetTester tester) async {
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) await tapKey(tester, 'menu-toggle');
  await tapKey(tester, 'nav-logbook');
}

/// Opens the continuation form from the "Planificar continuación" action of [activity] in Mi bitácora.
Future<void> openForm(WidgetTester tester, Activity activity) async {
  await goToLogbook(tester);
  await tapKey(tester, 'continuation-action-${activity.id}');
}

Future<void> describe(WidgetTester tester, String text) =>
    tester.enterText(find.byKey(const Key('continuation-description')), text);

Future<void> submit(WidgetTester tester) => tapKey(tester, 'continuation-submit');

/// Picks [day] of the month shown by the calendar (November 2026) in the date field [key].
Future<void> pickDay(WidgetTester tester, String key, String day) async {
  await tapKey(tester, key);
  await tester.tap(find.text(day));
  await tester.pumpAndSettle();
  await tester.tap(find.text('OK'));
  await tester.pumpAndSettle();
}

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

Finder statusPill(Activity activity, String label) =>
    find.descendant(of: find.byKey(Key('status-${activity.id}')), matching: find.text(label));

/// A repository with one activity planned for [date] (today by default).
({FakeLogbookRepository repo, Activity activity}) withActivity({
  DateTime? date,
  String title = 'Preparar informe',
  ActivityStatus status = ActivityStatus.pending,
}) {
  final repo = FakeLogbookRepository()..seed(date ?? today, title, description: 'Revisar cifras', status: status);
  return (repo: repo, activity: repo.days[formatDate(date ?? today)]!.activities.single);
}

String descriptionText(WidgetTester tester) =>
    tester.widget<TextField>(find.byKey(const Key('continuation-description'))).controller!.text;

void main() {
  setUpAll(loadTestFonts);

  group('the action', () {
    testWidgets('is offered on an eligible activity of Mi bitácora', (tester) async {
      for (final status in [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked]) {
        final s = withActivity(status: status);
        await pumpApp(tester, logbook: s.repo);
        await tapKey(tester, 'nav-logbook');
        expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsOneWidget, reason: status.name);
      }
    });

    testWidgets('is not offered on a Completada activity', (tester) async {
      final s = withActivity(status: ActivityStatus.completed);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsOneWidget); // the tile is there
      expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsNothing);
    });

    testWidgets('is not offered on an activity marked as an error', (tester) async {
      final s = withActivity();
      s.repo.markAsError(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('activity-${s.activity.id}')), findsOneWidget);
      expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsNothing);
    });

    testWidgets('opens the form with THAT activity shown, not chosen', (tester) async {
      final s = withActivity(title: 'Revisar requerimientos');
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      expect(find.text('Planificar continuación'), findsWidgets);
      expect(
        find.descendant(of: find.byKey(const Key('continuation-activity')), matching: find.text('Revisar requerimientos')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: find.byKey(const Key('continuation-activity-status')), matching: find.text('Pendiente')),
        findsOneWidget,
      );
    });

    testWidgets('the activity detail offers it too, and Cancelar goes back to the detail', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(const Key('detail-plan-continuation')), findsOneWidget);
      await tapKey(tester, 'detail-plan-continuation');
      expect(find.byKey(const Key('continuation-submit')), findsOneWidget);
      await tapKey(tester, 'continuation-cancel');
      expect(find.byKey(const Key('detail-status')), findsOneWidget);
      expect(s.repo.continuationRequests, isEmpty);
    });

    testWidgets('the detail of a Completada activity does not offer it', (tester) async {
      final s = withActivity(status: ActivityStatus.completed);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(const Key('detail-register-progress')), findsOneWidget);
      expect(find.byKey(const Key('detail-plan-continuation')), findsNothing);
    });

    testWidgets('the detail of an activity marked as an error does not offer it', (tester) async {
      final s = withActivity();
      s.repo.markAsError(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(const Key('detail-marked')), findsOneWidget);
      expect(find.byKey(const Key('detail-plan-continuation')), findsNothing);
    });
  });

  group('the form', () {
    testWidgets('starts at tomorrow with an empty description and no status to choose', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      expect(find.text(formatShortDate(tomorrow)), findsOneWidget);
      expect(descriptionText(tester), isEmpty);
      for (final status in ActivityStatus.values) {
        expect(find.byKey(Key('progress-status-${status.name}')), findsNothing); // it is not progress
      }
      expect(find.byKey(const Key('continuation-hint')), findsOneWidget);
    });

    testWidgets('a future day being looked at is the starting date', (tester) async {
      final s = withActivity();
      s.repo.addContinuation(s.activity.id, nextMonday, 'Ya prevista'); // the activity is listed on that day
      await pumpApp(tester, logbook: s.repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(nextMonday);
      await tester.pumpAndSettle();
      await openForm(tester, s.activity);
      expect(find.text(formatShortDate(nextMonday)), findsOneWidget);
    });

    testWidgets('the calendar does not offer today nor the past', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickDay(tester, 'continuation-date', '6'); // today: disabled
      expect(find.text(formatShortDate(tomorrow)), findsOneWidget);
      await pickDay(tester, 'continuation-date', '2'); // the past: disabled
      expect(find.text(formatShortDate(tomorrow)), findsOneWidget);
      expect(s.repo.continuationRequests, isEmpty);
    });

    testWidgets('a later day can be chosen', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickDay(tester, 'continuation-date', '9');
      expect(find.text(formatShortDate(nextMonday)), findsOneWidget);
    });

    testWidgets('without an activity chosen it explains so and offers no submit', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      containerOf(tester).read(currentPageProvider.notifier).go(AppPage.continuation);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('continuation-none')), findsOneWidget);
      expect(find.byKey(const Key('continuation-submit')), findsNothing);
    });

    testWidgets('a stale Completada target shows the notice and cannot be submitted', (tester) async {
      final s = withActivity(status: ActivityStatus.completed);
      await pumpApp(tester, logbook: s.repo);
      final container = containerOf(tester);
      container.read(continuationTargetProvider.notifier).select(s.activity.summary);
      container.read(currentPageProvider.notifier).go(AppPage.continuation);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('continuation-completed-notice')), findsOneWidget);
      await tester.ensureVisible(find.byKey(const Key('continuation-submit')));
      await tester.tap(find.byKey(const Key('continuation-submit')));
      await tester.pumpAndSettle();
      expect(s.repo.continuationRequests, isEmpty);
    });

    testWidgets('the form is not carried over: the next one starts empty', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, 'Algo a medias');
      await tapKey(tester, 'continuation-cancel');
      await tapKey(tester, 'continuation-action-${s.activity.id}');
      expect(descriptionText(tester), isEmpty);
    });
  });

  group('saving', () {
    testWidgets('sends the real request and the screen then shows what the server holds', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, '  Cerrar las cifras  ');
      await submit(tester);

      final request = s.repo.continuationRequests.single;
      expect(request['activityId'], s.activity.id);
      expect(request['date'], '2026-11-07');
      expect(request['description'], 'Cerrar las cifras');
      expect((request['key'] as String).length, 32);

      // Success: toast, back to Mi bitácora on the day it was planned for, read from the "server"
      expect(find.text('Continuación planificada.'), findsOneWidget);
      expect(find.byKey(const Key('logbook-new-activity')), findsOneWidget);
      expect(find.text(formatShortDate(tomorrow)), findsWidgets);
      expect(find.byKey(Key('continuation-line-${s.repo.days['2026-11-07']!.plannings.single.id}')), findsOneWidget);
      expect(find.text('Cerrar las cifras'), findsOneWidget);
    });

    testWidgets('the description is optional: it is sent as absent', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await submit(tester);
      expect(s.repo.continuationRequests.single['description'], isNull);
      expect(find.text('Sin descripción'), findsWidgets);
    });

    testWidgets('it plans a continuation: no other activity and no progress are created', (tester) async {
      final s = withActivity(status: ActivityStatus.inProgress);
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, 'Seguir mañana');
      await submit(tester);

      expect(s.repo.days.values.expand((d) => d.activities).map((a) => a.id).toSet(), {s.activity.id});
      expect(s.repo.progressStored(s.activity.id), isEmpty);
      final planned = s.repo.days['2026-11-07']!;
      expect(planned.progress, isEmpty);
      expect(planned.plannings.single.type, PlanningType.continuation);
      // The new day lists the SAME activity, with the status it already had
      expect(find.byKey(Key('activity-${s.activity.id}')), findsOneWidget);
      expect(statusPill(s.activity, 'En progreso'), findsOneWidget);
      expect(find.byWidgetPredicate((w) => w.key.toString().contains('progress-entry-')), findsNothing);
    });

    testWidgets('the activity keeps its status and its original day, and the dashboard indicators do not move', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      expect(stat(tester, 'Pendientes').value, 1);
      await openForm(tester, s.activity);
      await submit(tester);
      // Back on today's logbook: the original planning and the status are as they were
      containerOf(tester).read(selectedDateProvider.notifier).select(today);
      await tester.pumpAndSettle();
      expect(statusPill(s.activity, 'Pendiente'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Pendientes').value, 1);
      expect(stat(tester, 'En progreso').value, 0);
      expect(stat(tester, 'Completadas').value, 0);
    });

    testWidgets('from the detail it returns to the detail, reloaded from the API', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
      final detailCalls = s.repo.detailRequests.length;

      await tapKey(tester, 'detail-plan-continuation');
      await describe(tester, 'Retomar el lunes');
      await pickDay(tester, 'continuation-date', '9');
      await submit(tester);

      expect(find.text('Continuación planificada.'), findsOneWidget); // toast
      expect(s.repo.detailRequests.length, greaterThan(detailCalls)); // the detail was fetched again
      final continuationId = s.repo.days['2026-11-09']!.plannings.single.id;
      expect(find.byKey(Key('detail-planning-$continuationId')), findsOneWidget);
      expect(find.text('Retomar el lunes'), findsOneWidget);
      expect(find.text(formatShortDate(nextMonday)), findsWidgets);
      // The status and the progress history did not change
      expect(find.descendant(of: find.byKey(const Key('detail-status')), matching: find.text('Pendiente')), findsOneWidget);
      expect(find.byKey(const Key('detail-no-progress')), findsOneWidget);
      expect(find.byKey(const Key('detail-planning-original')), findsOneWidget);
    });

    testWidgets('a detail kept in memory is refreshed from the API', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      final container = containerOf(tester);
      final detail = container.listen(activityDetailProvider(s.activity.id), (previous, next) {});
      addTearDown(detail.close);
      await tester.pumpAndSettle();
      expect(detail.read().requireValue.plannedContinuations, isEmpty);
      final detailCalls = s.repo.detailRequests.length;

      await openForm(tester, s.activity);
      await describe(tester, 'Seguir');
      await submit(tester);

      expect(s.repo.detailRequests.length, greaterThan(detailCalls));
      final refreshed = container.read(activityDetailProvider(s.activity.id)).requireValue;
      expect(refreshed.plannedContinuations.map((p) => p.description), ['Seguir']);
      expect(refreshed.status, ActivityStatus.pending);
      expect(refreshed.progress, isEmpty);
    });

    testWidgets('several continuations of the same activity can be planned', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, 'Primera');
      await submit(tester);
      await tapKey(tester, 'continuation-action-${s.activity.id}');
      await pickDay(tester, 'continuation-date', '9');
      await describe(tester, 'Segunda');
      await submit(tester);
      expect(s.repo.continuationRequests, hasLength(2));
      expect(s.repo.continuationRequests.map((r) => r['key']).toSet(), hasLength(2)); // two intentions, two keys
      expect(s.repo.days['2026-11-07']!.plannings.single.description, 'Primera');
      expect(s.repo.days['2026-11-09']!.plannings.single.description, 'Segunda');
    });
  });

  group('original planning, continuation and progress look different', () {
    testWidgets('the detail tells them apart with their own tag, block and text', (tester) async {
      final s = withActivity();
      s.repo.addContinuation(s.activity.id, nextMonday, 'Terminar el informe');
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');

      final continuationId = s.repo.days['2026-11-09']!.plannings.single.id;
      final original = find.byKey(const Key('detail-planning-original'));
      final continuation = find.byKey(Key('detail-planning-$continuationId'));
      expect(original, findsOneWidget);
      expect(continuation, findsOneWidget);

      Color? background(Finder block) =>
          ((tester.widget<Container>(block)).decoration as BoxDecoration).color;
      expect(background(original), isNot(background(continuation)));

      expect(find.descendant(of: original, matching: find.text('Planificación original')), findsOneWidget);
      expect(find.descendant(of: continuation, matching: find.text('Continuación planificada')), findsOneWidget);
      // Only the continuation carries the tag; the original never does
      expect(find.descendant(of: continuation, matching: find.text('CONTINUACIÓN PLANIFICADA')), findsOneWidget);
      expect(find.descendant(of: original, matching: find.text('CONTINUACIÓN PLANIFICADA')), findsNothing);
      // And neither of them is in the progress history
      expect(find.byKey(const Key('detail-no-progress')), findsOneWidget);
    });

    testWidgets('a day shows the continuation apart from progress and apart from the original planning', (tester) async {
      final s = withActivity(status: ActivityStatus.inProgress);
      s.repo.addContinuation(s.activity.id, tomorrow, 'Seguir con el informe');
      await pumpApp(tester, logbook: s.repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await tapKey(tester, 'nav-logbook');

      final line = find.byWidgetPredicate((w) => w.key.toString().contains('continuation-line-'));
      expect(line, findsOneWidget);
      expect(find.descendant(of: line, matching: find.text('CONTINUACIÓN PLANIFICADA')), findsOneWidget);
      expect(find.descendant(of: line, matching: find.text('Seguir con el informe')), findsOneWidget);
      // The original planning text and time belong to another day: this one says where it started
      expect(find.byKey(Key('origin-day-${s.activity.id}')), findsOneWidget);
      expect(find.text('Revisar cifras'), findsNothing);
      expect(find.byWidgetPredicate((w) => w.key.toString().contains('progress-entry-')), findsNothing);
    });

    testWidgets('an unplanned activity continued on another day is not described as planned that day', (tester) async {
      final repo = FakeLogbookRepository();
      final created = await repo.registerUnplanned(
        date: today,
        title: 'Imprevisto',
        status: ActivityStatus.inProgress,
        description: 'Lo atendí',
        key: 'k-unplanned',
      );
      final id = created.activity.id;
      repo.addContinuation(id, tomorrow, 'Retomarlo');
      await pumpApp(tester, logbook: repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await tapKey(tester, 'nav-logbook');
      expect(find.text('Retomarlo'), findsOneWidget);
      expect(find.byKey(Key('origin-day-$id')), findsOneWidget);
    });
  });

  group('server errors', () {
    final cases = <(String, int, String)>[
      ('FECHA_NO_FUTURA', 422, 'La continuación planificada debe ser para una fecha posterior a hoy.'),
      ('FECHA_NO_CUBIERTA', 422, 'Esa fecha no está cubierta por tu pertenencia a un equipo.'),
      ('ACTIVIDAD_COMPLETADA', 409, 'La actividad está Completada. Hay que reactivarla antes de continuarla.'),
      ('ACTIVIDAD_MARCADA_POR_ERROR', 409, 'La actividad está marcada como registrada por error.'),
      ('RECURSO_NO_DISPONIBLE', 404, 'El recurso solicitado no está disponible.'),
      ('TEXTO_DEMASIADO_LARGO', 422, 'El texto supera el máximo permitido.'),
    ];
    for (final (code, status, message) in cases) {
      testWidgets('$code is explained with a clear message and the form stays editable', (tester) async {
        final s = withActivity();
        s.repo.continuationErrors.add(ApiError(code: code, message: 'x', status: status));
        await pumpApp(tester, logbook: s.repo);
        await openForm(tester, s.activity);
        await describe(tester, 'Seguir');
        await submit(tester);
        expect(tester.widget<Text>(find.byKey(const Key('continuation-error'))).data, message);
        expect(s.repo.days.containsKey('2026-11-07'), isFalse); // nothing was created
        expect(tester.widget<TextField>(find.byKey(const Key('continuation-description'))).enabled, isTrue);
        expect(descriptionText(tester), 'Seguir'); // what was typed is kept
      });
    }

    testWidgets('a network failure keeps what was typed and the retry reuses the SAME key', (tester) async {
      final s = withActivity();
      s.repo.continuationErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, 'Seguir');
      await submit(tester);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      await submit(tester);
      expect(find.byKey(const Key('continuation-error')), findsNothing);
      final keys = s.repo.continuationRequests.map((r) => r['key']).toList();
      expect(keys, hasLength(2));
      expect(keys[0], keys[1]); // one intention: the server can recognize the retry
      expect(s.repo.days['2026-11-07']!.plannings, hasLength(1));
    });

    testWidgets('changing what is sent gets a NEW key', (tester) async {
      final s = withActivity();
      s.repo.continuationErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, 'Seguir');
      await submit(tester);
      await describe(tester, 'Seguir, pero distinto');
      await submit(tester);
      final keys = s.repo.continuationRequests.map((r) => r['key']).toList();
      expect(keys[0], isNot(keys[1]));
    });

    testWidgets('an expired session sends the user back to the login', (tester) async {
      final s = withActivity();
      s.repo.continuationErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await submit(tester);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('while it is saving', () {
    testWidgets('shows the loading state, disables the form and ignores a second tap', (tester) async {
      final s = withActivity();
      final gate = Completer<void>();
      s.repo.continuationGate = gate;
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await describe(tester, 'Seguir');

      await tester.ensureVisible(find.byKey(const Key('continuation-submit')));
      await tester.tap(find.byKey(const Key('continuation-submit')));
      await tester.pump(); // the request is now in flight
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(tester.widget<TextField>(find.byKey(const Key('continuation-description'))).enabled, isFalse);
      await tester.tap(find.byKey(const Key('continuation-submit')), warnIfMissed: false);
      await tester.tap(find.byKey(const Key('continuation-cancel')), warnIfMissed: false);
      await tester.pump();
      expect(s.repo.continuationRequests, hasLength(1)); // the second tap did nothing
      expect(find.byKey(const Key('continuation-submit')), findsOneWidget); // Cancelar did not leave the form

      gate.complete();
      await tester.pumpAndSettle();
      expect(s.repo.continuationRequests, hasLength(1));
      expect(s.repo.days['2026-11-07']!.plannings, hasLength(1)); // exactly one continuation
    });
  });

  group('on a phone', () {
    testWidgets('the action, the form and the detail fit without overflowing', (tester) async {
      final s = withActivity(title: 'Preparar el informe mensual de resultados del equipo');
      s.repo.addContinuation(s.activity.id, nextMonday, 'Terminar el informe y enviarlo');
      await pumpApp(tester, logbook: s.repo, size: mobile);
      await goToLogbook(tester);
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(const Key('detail-plan-continuation')), findsOneWidget);
      await tapKey(tester, 'detail-plan-continuation');
      expect(find.byKey(const Key('continuation-submit')), findsOneWidget);
      await describe(tester, 'Un texto bastante largo para comprobar que el formulario se ajusta al ancho del móvil');
      await submit(tester);
      expect(tester.takeException(), isNull);
      expect(s.repo.continuationRequests, hasLength(1));
    });
  });
}
