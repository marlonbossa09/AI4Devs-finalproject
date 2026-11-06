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
import 'package:smartwork/features/logbook/presentation/providers/activity_list.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_notifier.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
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

/// Opens the unplanned form from the dashboard (its action is visible at any width).
Future<void> openForm(WidgetTester tester) => tapKey(tester, 'dashboard-new-unplanned');

Future<void> fill(WidgetTester tester, {String title = 'Atender incidente', String description = 'Revisé los registros'}) async {
  await tester.enterText(find.byKey(const Key('unplanned-title')), title);
  await tester.enterText(find.byKey(const Key('unplanned-description')), description);
}

Future<void> pick(WidgetTester tester, ActivityStatus status) => tapKey(tester, 'unplanned-status-${status.name}');

Future<void> submit(WidgetTester tester) => tapKey(tester, 'unplanned-submit');

/// Fills and sends a complete entry.
Future<void> register(
  WidgetTester tester, {
  String title = 'Atender incidente',
  ActivityStatus status = ActivityStatus.inProgress,
  String description = 'Revisé los registros',
}) async {
  await fill(tester, title: title, description: description);
  await pick(tester, status);
  await submit(tester);
}

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

Finder pill(String key, String label) => find.descendant(of: find.byKey(Key(key)), matching: find.text(label));

Finder tagOf(String key) => find.descendant(of: find.byKey(Key(key)), matching: find.text('No planificada'));

Activity activityOf(FakeLogbookRepository repo, String title) {
  for (final day in repo.days.values) {
    for (final activity in day.activities) {
      if (activity.title == title) return activity;
    }
  }
  throw StateError('No activity "$title"');
}

void main() {
  setUpAll(loadTestFonts);

  group('the action', () {
    testWidgets('is visible in the dashboard, in Mi bitácora and in the activity list', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      expect(find.byKey(const Key('dashboard-new-unplanned')), findsOneWidget);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(const Key('logbook-new-unplanned')), findsOneWidget);
      await tapKey(tester, 'nav-activities');
      expect(find.byKey(const Key('activities-new-unplanned')), findsOneWidget);
    });

    for (final (from, key) in [
      ('the dashboard', 'dashboard-new-unplanned'),
      ('Mi bitácora', 'logbook-new-unplanned'),
      ('the activity list', 'activities-new-unplanned'),
    ]) {
      testWidgets('opens the form from $from', (tester) async {
        await pumpApp(tester, logbook: FakeLogbookRepository());
        if (key.startsWith('logbook')) await tapKey(tester, 'nav-logbook');
        if (key.startsWith('activities')) await tapKey(tester, 'nav-activities');
        await tapKey(tester, key);
        expect(find.byKey(const Key('unplanned-submit')), findsOneWidget);
        expect(find.text('ACTIVIDAD NO PLANIFICADA'), findsNothing); // the heading is not the tag
        expect(find.text('Actividad no planificada'), findsWidgets);
      });
    }

    testWidgets('both header actions are still reachable and the planning one is unchanged', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await tapKey(tester, 'dashboard-new-planning');
      expect(find.byKey(const Key('plan-submit')), findsOneWidget);
    });
  });

  group('the form', () {
    testWidgets('has the fields of the contract, says there is no planning, and chooses nothing for the user', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openForm(tester);
      for (final key in ['unplanned-title', 'unplanned-date', 'unplanned-description']) {
        expect(find.byKey(Key(key)), findsOneWidget, reason: key);
      }
      for (final status in ActivityStatus.values) {
        expect(find.byKey(Key('unplanned-status-${status.name}')), findsOneWidget);
        expect(
          find.descendant(of: find.byKey(Key('unplanned-status-${status.name}')), matching: find.byIcon(Icons.check)),
          findsNothing,
        );
      }
      expect(find.byKey(const Key('unplanned-reason')), findsNothing);
      expect(find.byKey(const Key('unplanned-notice')), findsOneWidget);
      expect(find.text(formatShortDate(today)), findsOneWidget);
    });

    testWidgets('an empty submit shows what is missing and sends nothing', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await submit(tester);
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      expect(find.text('Elige un estado.'), findsOneWidget);
      expect(find.text('Describe el trabajo realizado.'), findsOneWidget);
      expect(repo.unplannedRequests, isEmpty);
    });

    testWidgets('a title of only spaces is not accepted (CA-296)', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, title: '     ');
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      expect(repo.unplannedRequests, isEmpty);
    });

    testWidgets('a description of only spaces is not accepted (CA-58)', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, description: '    ');
      expect(find.text('Describe el trabajo realizado.'), findsOneWidget);
      expect(repo.unplannedRequests, isEmpty);
    });

    testWidgets('the reason appears only for Bloqueada and is required (CA-55)', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      expect(find.byKey(const Key('unplanned-reason')), findsNothing);
      await pick(tester, ActivityStatus.blocked);
      expect(find.byKey(const Key('unplanned-reason')), findsOneWidget);
      await fill(tester);
      await submit(tester);
      expect(find.text('Indica el motivo del bloqueo.'), findsOneWidget);
      expect(repo.unplannedRequests, isEmpty);
      await pick(tester, ActivityStatus.completed);
      expect(find.byKey(const Key('unplanned-reason')), findsNothing);
    });

    testWidgets('a reason typed for Bloqueada is discarded if the status changes: it is never sent', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await pick(tester, ActivityStatus.blocked);
      await tester.enterText(find.byKey(const Key('unplanned-reason')), 'Falta acceso');
      await pick(tester, ActivityStatus.inProgress);
      await fill(tester);
      await submit(tester);
      expect(repo.unplannedRequests.single['blockReason'], isNull);
    });

    for (final status in ActivityStatus.values) {
      testWidgets('the status ${status.name} is accepted and becomes the activity status (CA-44, CA-54)', (tester) async {
        final repo = FakeLogbookRepository();
        await pumpApp(tester, logbook: repo);
        await openForm(tester);
        await fill(tester);
        await pick(tester, status);
        if (status == ActivityStatus.blocked) {
          await tester.enterText(find.byKey(const Key('unplanned-reason')), 'Falta acceso');
        }
        await submit(tester);
        expect(repo.unplannedRequests.single['status'], status);
        expect(activityOf(repo, 'Atender incidente').status, status);
      });
    }

    testWidgets('a future day being looked at starts the form at today (no future execution)', (tester) async {
      final repo = FakeLogbookRepository()..seed(tomorrow, 'Para mañana');
      await pumpApp(tester, logbook: repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await openForm(tester);
      expect(find.text(formatShortDate(today)), findsOneWidget);
      expect(find.text(formatShortDate(tomorrow)), findsNothing);
    });

    testWidgets('the calendar does not offer future dates', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openForm(tester);
      await tapKey(tester, 'unplanned-date');
      await tester.tap(find.text('7')); // tomorrow: disabled
      await tester.pumpAndSettle();
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(find.text(formatShortDate(today)), findsOneWidget);
      expect(find.text(formatShortDate(tomorrow)), findsNothing);
    });

    testWidgets('cancelling goes back to the dashboard without sending anything', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await tapKey(tester, 'unplanned-cancel');
      expect(find.byKey(const Key('dashboard-new-planning')), findsOneWidget);
      expect(repo.unplannedRequests, isEmpty);
    });
  });

  group('saving', () {
    testWidgets('sends the real request and the screen then shows what the server holds', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, title: '  Atender incidente  ', description: '  Revisé los registros  ');
      final request = repo.unplannedRequests.single;
      expect(request['date'], '2026-11-06');
      expect(request['title'], 'Atender incidente');
      expect(request['status'], ActivityStatus.inProgress);
      expect(request['description'], 'Revisé los registros');
      expect((request['key'] as String).length, 32);
      // Success: toast, back to Mi bitácora, and the activity as the server holds it
      expect(find.text('Actividad no planificada registrada.'), findsOneWidget);
      expect(find.byKey(const Key('logbook-new-planning')), findsOneWidget);
      final activity = activityOf(repo, 'Atender incidente');
      expect(pill('status-${activity.id}', 'En progreso'), findsOneWidget);
      expect(find.textContaining('Avance · En progreso: Revisé los registros'), findsOneWidget);
    });

    testWidgets('the unplanned activity is tagged and carries no invented planning', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Prevista', description: 'Revisar cifras');
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester);
      final unplanned = activityOf(repo, 'Atender incidente');
      final planned = activityOf(repo, 'Prevista');
      // Tagged apart from the planned one
      expect(tagOf('origin-${unplanned.id}'), findsOneWidget);
      expect(tagOf('origin-${planned.id}'), findsNothing);
      expect(find.text('Registrada sin planificación previa.'), findsOneWidget); // never "Sin descripción"
      expect(find.text('Revisar cifras'), findsOneWidget); // the planned one keeps its planning
      // The server holds no planning for it
      expect(repo.days[formatDate(today)]!.plannings.where((p) => p.activityId == unplanned.id), isEmpty);
      // Its first entry is shown, and the tile says it was registered, not planned
      expect(find.textContaining('Registrada '), findsWidgets);
      expect(unplanned.origin, ActivityOrigin.unplanned);
    });

    testWidgets('its status is one of the four: being unplanned is not a status', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, status: ActivityStatus.completed);
      final activity = activityOf(repo, 'Atender incidente');
      expect(pill('status-${activity.id}', 'Completada'), findsOneWidget);
      expect(find.descendant(of: find.byKey(Key('status-${activity.id}')), matching: find.text('No planificada')), findsNothing);
    });

    testWidgets('the dashboard indicators follow the new activity', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      expect(stat(tester, 'Actividades registradas').value, 0);
      await openForm(tester);
      await register(tester, status: ActivityStatus.completed);
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Actividades registradas').value, 1);
      expect(stat(tester, 'Completadas').value, 1);
      expect(stat(tester, 'Pendientes').value, 0);
    });

    testWidgets('the dashboard counts it by the status of its first entry', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Prevista');
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, status: ActivityStatus.inProgress);
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Actividades registradas').value, 2);
      expect(stat(tester, 'Pendientes').value, 1);
      expect(stat(tester, 'En progreso').value, 1);
    });

    testWidgets('blocking sends the reason and the entry shows it', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await fill(tester);
      await pick(tester, ActivityStatus.blocked);
      await tester.enterText(find.byKey(const Key('unplanned-reason')), 'Falta el acceso al servidor');
      await submit(tester);
      expect(repo.unplannedRequests.single['blockReason'], 'Falta el acceso al servidor');
      expect(find.text('Motivo del bloqueo: Falta el acceso al servidor'), findsOneWidget); // CA-56
    });

    testWidgets('the activity list shows it, tagged and newest first', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Prevista');
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester);
      await tapKey(tester, 'nav-activities');
      final unplanned = activityOf(repo, 'Atender incidente');
      final planned = activityOf(repo, 'Prevista');
      expect(find.text('Actividad no planificada'), findsWidgets);
      expect(tagOf('row-origin-${unplanned.id}'), findsOneWidget);
      expect(tagOf('row-origin-${planned.id}'), findsNothing);
      expect(pill('row-status-${unplanned.id}', 'En progreso'), findsOneWidget);
      final top = tester.getTopLeft(find.byKey(Key('activity-row-${unplanned.id}'))).dy;
      expect(top, lessThan(tester.getTopLeft(find.byKey(Key('activity-row-${planned.id}'))).dy)); // newest first
    });

    testWidgets('its detail has no planning, shows the first entry and the tag', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, description: 'Primer avance');
      final activity = activityOf(repo, 'Atender incidente');
      await tapKey(tester, 'activity-open-${activity.id}');
      expect(find.byKey(const Key('detail-origin-tag')), findsOneWidget);
      expect(find.byKey(const Key('detail-no-planning')), findsOneWidget);
      expect(find.byKey(const Key('detail-planning-original')), findsNothing);
      expect(find.text('Primer avance'), findsOneWidget);
      expect(pill('detail-status', 'En progreso'), findsOneWidget);
    });

    testWidgets('a past date is registered on that day, picked from the calendar', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await tapKey(tester, 'unplanned-date');
      await tester.tap(find.text('5'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(find.text(formatShortDate(yesterday)), findsOneWidget);
      await register(tester, title: 'Del jueves');
      expect(repo.unplannedRequests.single['date'], '2026-11-05');
      // It lands on the day it belongs to, which becomes the one shown
      expect(find.text(formatShortDate(yesterday)), findsWidgets);
      expect(find.text('Del jueves'), findsOneWidget);
    });

    testWidgets('the form starts empty for the next entry', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester);
      await tapKey(tester, 'logbook-new-unplanned');
      expect(tester.widget<TextField>(find.byKey(const Key('unplanned-title'))).controller!.text, isEmpty);
      expect(tester.widget<TextField>(find.byKey(const Key('unplanned-description'))).controller!.text, isEmpty);
      expect(find.text('Elige un estado.'), findsNothing);
    });
  });

  group('server errors', () {
    final cases = <(String, int, String)>[
      ('CAMPO_OBLIGATORIO', 422, 'Falta un campo obligatorio.'),
      ('FECHA_FUTURA_NO_PERMITIDA', 422, 'No se puede registrar ejecución ni cerrar una jornada de fecha futura.'),
      ('FECHA_NO_CUBIERTA', 422, 'Esa fecha no está cubierta por tu pertenencia a un equipo.'),
      ('BITACORA_CERRADA', 409, 'La bitácora de esa fecha está cerrada. Hay que reabrirla antes de modificarla.'),
      ('ESTADO_INVALIDO', 422, 'El estado elegido no es válido.'),
      ('DESCRIPCION_OBLIGATORIA', 422, 'Describe el trabajo realizado.'),
      ('MOTIVO_BLOQUEO_OBLIGATORIO', 422, 'Indica el motivo del bloqueo.'),
      ('TEXTO_DEMASIADO_LARGO', 422, 'El texto supera el máximo permitido.'),
    ];
    for (final (code, status, message) in cases) {
      testWidgets('$code is explained and the form stays editable', (tester) async {
        final repo = FakeLogbookRepository();
        repo.unplannedErrors.add(ApiError(code: code, message: 'x', status: status));
        await pumpApp(tester, logbook: repo);
        await openForm(tester);
        await register(tester);
        expect(tester.widget<Text>(find.byKey(const Key('unplanned-error'))).data, message);
        expect(repo.days, isEmpty); // nothing was created
        expect(tester.widget<TextField>(find.byKey(const Key('unplanned-title'))).enabled, isTrue);
        expect(tester.widget<TextField>(find.byKey(const Key('unplanned-title'))).controller!.text, 'Atender incidente');
      });
    }

    testWidgets('a network failure keeps what was typed and can be retried', (tester) async {
      final repo = FakeLogbookRepository();
      repo.unplannedErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      await submit(tester);
      expect(find.byKey(const Key('unplanned-error')), findsNothing);
      expect(repo.days.values.expand((d) => d.activities), hasLength(1));
    });

    testWidgets('an expired session sends the user back to the login', (tester) async {
      final repo = FakeLogbookRepository();
      repo.unplannedErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('while it is saving', () {
    testWidgets('shows the loading state, disables the form and ignores a second tap', (tester) async {
      final repo = FakeLogbookRepository();
      repo.unplannedGate = Completer<void>();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await fill(tester);
      await pick(tester, ActivityStatus.inProgress);
      await tester.ensureVisible(find.byKey(const Key('unplanned-submit')));
      await tester.tap(find.byKey(const Key('unplanned-submit')));
      await tester.pump();
      expect(
        find.descendant(of: find.byKey(const Key('unplanned-submit')), matching: find.byType(CircularProgressIndicator)),
        findsOneWidget,
      );
      expect(tester.widget<TextField>(find.byKey(const Key('unplanned-title'))).enabled, isFalse);
      expect(tester.widget<TextField>(find.byKey(const Key('unplanned-description'))).enabled, isFalse);
      // Impatient taps while it runs
      await tester.tap(find.byKey(const Key('unplanned-submit')), warnIfMissed: false);
      await tester.pump();
      await tester.tap(find.byKey(const Key('unplanned-submit')), warnIfMissed: false);
      await tester.pump();
      expect(repo.unplannedRequests, hasLength(1));
      repo.unplannedGate!.complete();
      await tester.pumpAndSettle();
      expect(repo.unplannedRequests, hasLength(1));
      expect(repo.days.values.expand((d) => d.activities), hasLength(1)); // one activity, not three
      expect(find.text('Actividad no planificada registrada.'), findsOneWidget);
    });

    testWidgets('the cancel action is blocked until the request ends', (tester) async {
      final repo = FakeLogbookRepository();
      repo.unplannedGate = Completer<void>();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await fill(tester);
      await pick(tester, ActivityStatus.inProgress);
      await tester.ensureVisible(find.byKey(const Key('unplanned-submit')));
      await tester.tap(find.byKey(const Key('unplanned-submit')));
      await tester.pump();
      expect(
        tester.widget<OutlinedButton>(find.descendant(of: find.byKey(const Key('unplanned-cancel')), matching: find.byType(OutlinedButton))).onPressed,
        isNull,
      );
      repo.unplannedGate!.complete();
      await tester.pumpAndSettle();
    });
  });

  group('idempotency key (T-04)', () {
    testWidgets('a retry of the same request reuses the key and the server creates it once', (tester) async {
      final repo = FakeLogbookRepository();
      repo.unplannedErrors.addAll([const ApiError(code: ApiError.network, message: 'x'), null]);
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester);
      await submit(tester);
      final keys = [for (final r in repo.unplannedRequests) r['key']];
      expect(keys, hasLength(2));
      expect(keys[0], keys[1]);
      expect(repo.days.values.expand((d) => d.activities), hasLength(1));
    });

    testWidgets('changing what is sent after a failure is a different intention: new key', (tester) async {
      final repo = FakeLogbookRepository();
      repo.unplannedErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, title: 'Primera versión');
      await tester.enterText(find.byKey(const Key('unplanned-title')), 'Segunda versión');
      await submit(tester);
      final keys = [for (final r in repo.unplannedRequests) r['key']];
      expect(keys[0], isNot(keys[1]));
    });

    testWidgets('after a success the next one is a new intention with its own key, even if identical', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      await openForm(tester);
      await register(tester, title: 'Igual');
      await tapKey(tester, 'logbook-new-unplanned');
      await register(tester, title: 'Igual');
      final keys = [for (final r in repo.unplannedRequests) r['key']];
      expect(keys, hasLength(2));
      expect(keys[0], isNot(keys[1]));
      expect(repo.days.values.expand((d) => d.activities), hasLength(2)); // two activities, as intended
    });
  });

  group('data refresh', () {
    test('registering reloads every watched day, the activity list and a detail that is open', () async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'Prevista');
      final planned = activityOf(repo, 'Prevista');
      final container = ProviderContainer(
        retry: noAutomaticRetry,
        overrides: [logbookRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      final otherDay = container.listen(logbookProvider(yesterday), (previous, next) {});
      final list = container.listen(activityListProvider, (previous, next) {});
      final detail = container.listen(activityDetailProvider(planned.id), (previous, next) {});
      await container.read(logbookProvider(yesterday).future);
      await container.read(activityListProvider.future);
      await container.read(activityDetailProvider(planned.id).future);
      expect(list.read().requireValue.items, hasLength(1));
      final readsBefore = repo.calls.where((c) => c.startsWith('get ')).length;

      final saved = container.listen(logbookProvider(today), (previous, next) {});
      await container.read(logbookProvider(today).notifier).registerUnplanned(
        title: 'Atender incidente',
        status: ActivityStatus.blocked,
        description: 'Me detuve',
        blockReason: 'Falta acceso',
        key: 'k-1',
      );
      await container.read(activityListProvider.future);

      expect(list.read().requireValue.items.map((i) => i.title), ['Atender incidente', 'Prevista']);
      expect(list.read().requireValue.items.first.origin, ActivityOrigin.unplanned);
      expect(saved.read().value!.activities.single.status, ActivityStatus.blocked);
      expect(repo.calls.where((c) => c.startsWith('get ')).length, greaterThan(readsBefore)); // other days reloaded
      expect(otherDay.read().value!.activities.single.title, 'Prevista');
      expect(detail.read().requireValue.activity.title, 'Prevista');
      expect(repo.detailRequests.length, 2); // the open detail was reloaded from the API too
    });
  });

  group('responsive', () {
    for (final (name, size) in [('tablet', tablet), ('mobile', mobile)]) {
      testWidgets('the whole flow works on $name without layout errors', (tester) async {
        final repo = FakeLogbookRepository();
        await pumpApp(tester, logbook: repo, size: size);
        expect(tester.takeException(), isNull); // the header with two actions fits
        await openForm(tester);
        expect(find.byKey(const Key('unplanned-submit')), findsOneWidget);
        await fill(tester, title: 'Un imprevisto con un título bastante largo para comprobar el ajuste en pantallas estrechas');
        await pick(tester, ActivityStatus.blocked);
        await tester.enterText(find.byKey(const Key('unplanned-reason')), 'Falta el acceso al servidor de pruebas');
        await submit(tester);
        final activity = repo.days.values.expand((d) => d.activities).single;
        expect(activity.status, ActivityStatus.blocked);
        expect(tagOf('origin-${activity.id}'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
