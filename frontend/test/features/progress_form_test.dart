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
import 'package:smartwork/features/logbook/presentation/providers/logbook_notifier.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final yesterday = DateTime.utc(2026, 11, 5);
final tomorrow = DateTime.utc(2026, 11, 7);

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

/// Opens the progress form from the "Registrar avance" action of [activity] in Mi bitácora.
Future<void> openForm(WidgetTester tester, Activity activity) async {
  await tapKey(tester, 'nav-logbook');
  await tapKey(tester, 'progress-action-${activity.id}');
}

Future<void> pickStatus(WidgetTester tester, ActivityStatus status) => tapKey(tester, 'progress-status-${status.name}');

Future<void> describe(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(const Key('progress-description')), text);
}

Future<void> submit(WidgetTester tester) => tapKey(tester, 'progress-submit');

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

Finder statusPill(Activity activity, String label) =>
    find.descendant(of: find.byKey(Key('status-${activity.id}')), matching: find.text(label));

/// A repository with one pending activity planned for [date] (today by default).
({FakeLogbookRepository repo, Activity activity}) withActivity({DateTime? date, String title = 'Preparar informe'}) {
  final repo = FakeLogbookRepository()..seed(date ?? today, title, description: 'Revisar cifras');
  return (repo: repo, activity: repo.days[formatDate(date ?? today)]!.activities.single);
}

void main() {
  setUpAll(loadTestFonts);

  group('the action', () {
    testWidgets('is visible on every activity of Mi bitácora and of the dashboard', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsOneWidget); // dashboard
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('progress-action-${s.activity.id}')), findsOneWidget); // logbook
    });

    testWidgets('opens the form with that activity already chosen', (tester) async {
      final s = withActivity(title: 'Revisar requerimientos');
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      expect(find.text('Registrar avance'), findsWidgets);
      expect(find.descendant(of: find.byKey(const Key('progress-activity')), matching: find.text('Revisar requerimientos')),
          findsOneWidget);
    });

    testWidgets('the dashboard action opens the same form', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'progress-action-${s.activity.id}');
      expect(find.byKey(const Key('progress-submit')), findsOneWidget);
    });
  });

  group('the form', () {
    testWidgets('offers the four states and only the activities of the day, and starts at today', (tester) async {
      final s = withActivity();
      s.repo.seed(yesterday, 'De ayer'); // another day: not offered
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      for (final status in ActivityStatus.values) {
        expect(find.byKey(Key('progress-status-${status.name}')), findsOneWidget);
      }
      expect(find.text('Pendiente'), findsWidgets);
      expect(find.text('En progreso'), findsWidgets);
      expect(find.text('Bloqueada'), findsWidgets);
      expect(find.text('Completada'), findsWidgets);
      expect(find.text(formatShortDate(today)), findsOneWidget);
      // Nothing is chosen for the user: no status is selected and there is no reason field
      for (final status in ActivityStatus.values) {
        expect(
          find.descendant(of: find.byKey(Key('progress-status-${status.name}')), matching: find.byIcon(Icons.check)),
          findsNothing,
          reason: status.name,
        );
      }
      expect(find.byKey(const Key('progress-reason')), findsNothing);
    });

    testWidgets('selecting a status marks it, and only that one', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await pickStatus(tester, ActivityStatus.completed);
      Finder selectedOf(ActivityStatus status) => find.descendant(
        of: find.byKey(Key('progress-status-${status.name}')),
        matching: find.byIcon(Icons.check),
      );
      expect(selectedOf(ActivityStatus.completed), findsOneWidget);
      expect(selectedOf(ActivityStatus.inProgress), findsNothing);
      expect(selectedOf(ActivityStatus.pending), findsNothing);
    });

    testWidgets('an empty submit shows what is missing and sends nothing (RN-70)', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await submit(tester);
      expect(find.text('Elige un estado.'), findsOneWidget);
      expect(find.text('Describe el trabajo realizado.'), findsOneWidget);
      expect(s.repo.progressRequests, isEmpty);
    });

    testWidgets('a description of only spaces is not accepted (CA-69)', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, '     ');
      await submit(tester);
      expect(find.text('Describe el trabajo realizado.'), findsOneWidget);
      expect(s.repo.progressRequests, isEmpty);
    });

    testWidgets('the reason appears only for Bloqueada and is required (CA-49)', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      expect(find.byKey(const Key('progress-reason')), findsNothing);
      await pickStatus(tester, ActivityStatus.blocked);
      expect(find.byKey(const Key('progress-reason')), findsOneWidget);
      await describe(tester, 'Me detuve');
      await submit(tester);
      expect(find.text('Indica el motivo del bloqueo.'), findsOneWidget);
      expect(s.repo.progressRequests, isEmpty);
      // Any other status hides it again
      await pickStatus(tester, ActivityStatus.inProgress);
      expect(find.byKey(const Key('progress-reason')), findsNothing);
    });

    testWidgets('a reason typed for Bloqueada is discarded if the status changes: it is never sent', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.blocked);
      await tester.enterText(find.byKey(const Key('progress-reason')), 'Falta acceso');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Sigo adelante');
      await submit(tester);
      expect(s.repo.progressRequests.single['blockReason'], isNull);
      expect(s.repo.progressRequests.single['status'], ActivityStatus.inProgress);
    });

    testWidgets('a completed activity says that it cannot be continued without reactivating it', (tester) async {
      final s = withActivity();
      s.repo.seed(today, 'Ya terminada', status: ActivityStatus.completed);
      await pumpApp(tester, logbook: s.repo);
      final done = s.repo.days[formatDate(today)]!.activities.last;
      await openForm(tester, done);
      expect(find.byKey(const Key('progress-completed-notice')), findsOneWidget);
    });

    testWidgets('a day without activities explains what to do and cannot be submitted', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      // No tile to start from, so the page is opened through the app state
      containerOf(tester).read(currentPageProvider.notifier).go(AppPage.progress);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('progress-no-activities')), findsOneWidget);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');
      await submit(tester);
      expect(find.text('Elige la actividad.'), findsOneWidget);
      expect(repo.progressRequests, isEmpty);
    });

    testWidgets('a future day being looked at starts the form at today (no future execution)', (tester) async {
      final s = withActivity(date: tomorrow, title: 'Para mañana');
      await pumpApp(tester, logbook: s.repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await openForm(tester, s.activity);
      expect(find.text(formatShortDate(today)), findsOneWidget);
      expect(find.text(formatShortDate(tomorrow)), findsNothing);
    });

    testWidgets('the calendar does not offer future dates', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await tapKey(tester, 'progress-date');
      await tester.tap(find.text('7')); // tomorrow: disabled
      await tester.pumpAndSettle();
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(find.text(formatShortDate(today)), findsOneWidget);
      expect(find.text(formatShortDate(tomorrow)), findsNothing);
    });
  });

  group('saving', () {
    testWidgets('sends the real request and the screen then shows what the server holds', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, '  Avancé con el informe  ');
      await submit(tester);

      final request = s.repo.progressRequests.single;
      expect(request['activityId'], s.activity.id);
      expect(request['date'], '2026-11-06');
      expect(request['status'], ActivityStatus.inProgress);
      expect(request['description'], 'Avancé con el informe');
      expect((request['key'] as String).length, 32);

      // Success: toast, back to Mi bitácora, new status and the entry, all from the "server"
      expect(find.text('Avance registrado.'), findsOneWidget);
      expect(find.byKey(const Key('logbook-new-planning')), findsOneWidget);
      expect(statusPill(s.activity, 'En progreso'), findsOneWidget);
      expect(find.textContaining('Avance · En progreso: Avancé con el informe'), findsOneWidget);
      expect(s.repo.progressStored(s.activity.id), hasLength(1));
    });

    testWidgets('the dashboard indicators follow the new status', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      expect(stat(tester, 'Pendientes').value, 1);
      expect(stat(tester, 'En progreso').value, 0);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');
      await submit(tester);
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Pendientes').value, 0);
      expect(stat(tester, 'En progreso').value, 1);
      expect(stat(tester, 'Completadas').value, 0);
    });

    testWidgets('completing an activity updates the Completadas indicator', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.completed);
      await describe(tester, 'Terminé');
      await submit(tester);
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Completadas').value, 1);
      expect(stat(tester, 'Pendientes').value, 0);
    });

    testWidgets('blocking sends the reason and the entry shows it', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.blocked);
      await tester.enterText(find.byKey(const Key('progress-reason')), 'Falta el acceso al servidor');
      await describe(tester, 'Me detuve');
      await submit(tester);
      expect(s.repo.progressRequests.single['blockReason'], 'Falta el acceso al servidor');
      expect(statusPill(s.activity, 'Bloqueada'), findsOneWidget);
      expect(find.text('Motivo del bloqueo: Falta el acceso al servidor'), findsOneWidget);
    });

    testWidgets('a retroactive entry is sent with its past date and the form is cleared afterwards', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await tapKey(tester, 'progress-date');
      await tester.tap(find.text('5'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(find.text(formatShortDate(yesterday)), findsOneWidget);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Trabajo de ayer');
      await submit(tester);
      expect(s.repo.progressRequests.single['date'], '2026-11-05');
      // It lands on the day it belongs to, which becomes the one shown
      expect(find.textContaining('Avance · En progreso: Trabajo de ayer'), findsOneWidget);
      expect(find.text(formatShortDate(yesterday)), findsWidgets);
      // The form starts empty for the next entry
      await tapKey(tester, 'progress-action-${s.activity.id}');
      expect(tester.widget<TextField>(find.byKey(const Key('progress-description'))).controller!.text, isEmpty);
      expect(find.text('Elige un estado.'), findsNothing);
    });

    testWidgets('after a completion the server rejects a later entry and the screen explains why (CA-190)', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.completed);
      await describe(tester, 'Terminé');
      await submit(tester);

      await tapKey(tester, 'progress-action-${s.activity.id}');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Quise seguir');
      await submit(tester);
      expect(find.text('La actividad está Completada. Hay que reactivarla antes de continuarla.'), findsOneWidget);
      expect(s.repo.progressStored(s.activity.id), hasLength(1)); // nothing was added
      expect(find.byKey(const Key('progress-submit')), findsOneWidget); // still in the form, to correct it
    });
  });

  group('server errors', () {
    final cases = <(String, int, String)>[
      ('FECHA_FUTURA_NO_PERMITIDA', 422, 'No se puede registrar ejecución ni cerrar una jornada de fecha futura.'),
      ('BITACORA_CERRADA', 409, 'La bitácora de esa fecha está cerrada. Hay que reabrirla antes de modificarla.'),
      ('ACTIVIDAD_MARCADA_POR_ERROR', 409, 'La actividad está marcada como registrada por error.'),
      ('RECURSO_NO_DISPONIBLE', 404, 'El recurso solicitado no está disponible.'),
      ('MOTIVO_BLOQUEO_OBLIGATORIO', 422, 'Indica el motivo del bloqueo.'),
      ('DESCRIPCION_OBLIGATORIA', 422, 'Describe el trabajo realizado.'),
      ('ESTADO_INVALIDO', 422, 'El estado elegido no es válido.'),
      ('TEXTO_DEMASIADO_LARGO', 422, 'El texto supera el máximo permitido.'),
    ];
    for (final (code, status, message) in cases) {
      testWidgets('$code is explained with a clear message and the form stays editable', (tester) async {
        final s = withActivity();
        s.repo.progressErrors.add(ApiError(code: code, message: 'x', status: status));
        await pumpApp(tester, logbook: s.repo);
        await openForm(tester, s.activity);
        await pickStatus(tester, ActivityStatus.inProgress);
        await describe(tester, 'Avancé');
        await submit(tester);
        expect(find.byKey(const Key('progress-error')), findsOneWidget);
        expect(tester.widget<Text>(find.byKey(const Key('progress-error'))).data, message);
        expect(s.repo.progressStored(s.activity.id), isEmpty);
        expect(tester.widget<TextField>(find.byKey(const Key('progress-description'))).enabled, isTrue);
      });
    }

    testWidgets('a network failure keeps what was typed and can be retried', (tester) async {
      final s = withActivity();
      s.repo.progressErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');
      await submit(tester);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      expect(tester.widget<TextField>(find.byKey(const Key('progress-description'))).controller!.text, 'Avancé');
      await submit(tester);
      expect(find.byKey(const Key('progress-error')), findsNothing);
      expect(s.repo.progressStored(s.activity.id), hasLength(1));
    });

    testWidgets('an expired session sends the user back to the login', (tester) async {
      final s = withActivity();
      s.repo.progressErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');
      await submit(tester);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('while it is saving', () {
    testWidgets('shows the loading state, disables the form and ignores a second tap', (tester) async {
      final s = withActivity();
      final gate = Completer<void>();
      s.repo.progressGate = gate;
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');

      await tester.ensureVisible(find.byKey(const Key('progress-submit')));
      await tester.tap(find.byKey(const Key('progress-submit')));
      await tester.pump(); // the request is now in flight
      expect(
        find.descendant(of: find.byKey(const Key('progress-submit')), matching: find.byType(CircularProgressIndicator)),
        findsOneWidget,
      );
      expect(tester.widget<TextField>(find.byKey(const Key('progress-description'))).enabled, isFalse);

      // Impatient taps while it is running
      await tester.tap(find.byKey(const Key('progress-submit')), warnIfMissed: false);
      await tester.pump();
      await tester.tap(find.byKey(const Key('progress-submit')), warnIfMissed: false);
      await tester.pump();
      expect(s.repo.progressRequests, hasLength(1));

      gate.complete();
      await tester.pumpAndSettle();
      expect(s.repo.progressRequests, hasLength(1));
      expect(s.repo.progressStored(s.activity.id), hasLength(1));
      expect(find.text('Avance registrado.'), findsOneWidget);
    });

    testWidgets('the cancel action is blocked until the request ends', (tester) async {
      final s = withActivity();
      s.repo.progressGate = Completer<void>();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');
      await tester.ensureVisible(find.byKey(const Key('progress-submit')));
      await tester.tap(find.byKey(const Key('progress-submit')));
      await tester.pump();
      expect(tester.widget<OutlinedButton>(find.descendant(of: find.byKey(const Key('progress-cancel')), matching: find.byType(OutlinedButton))).onPressed, isNull);
      s.repo.progressGate!.complete();
      await tester.pumpAndSettle();
    });
  });

  group('idempotency key (T-04)', () {
    testWidgets('a retry of the same request reuses the key and the server stores it once', (tester) async {
      final s = withActivity();
      s.repo.progressErrors.addAll([const ApiError(code: ApiError.network, message: 'x'), null]);
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Avancé');
      await submit(tester); // fails: the response never arrived
      await submit(tester); // the same intention
      final keys = [for (final r in s.repo.progressRequests) r['key']];
      expect(keys, hasLength(2));
      expect(keys[0], keys[1]);
      expect(s.repo.progressStored(s.activity.id), hasLength(1));
    });

    testWidgets('changing what is sent after a failure is a different intention: new key', (tester) async {
      final s = withActivity();
      s.repo.progressErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Primera versión');
      await submit(tester);
      await describe(tester, 'Segunda versión');
      await submit(tester);
      final keys = [for (final r in s.repo.progressRequests) r['key']];
      expect(keys[0], isNot(keys[1]));
    });

    testWidgets('after a success the next entry is a new intention with its own key', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Mismo texto');
      await submit(tester);
      await tapKey(tester, 'progress-action-${s.activity.id}');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Mismo texto');
      await submit(tester);
      final keys = [for (final r in s.repo.progressRequests) r['key']];
      expect(keys, hasLength(2));
      expect(keys[0], isNot(keys[1]));
      expect(s.repo.progressStored(s.activity.id), hasLength(2)); // two entries, as intended
    });

    testWidgets('every request carries its own random 128-bit key', (tester) async {
      final s = withActivity();
      await pumpApp(tester, logbook: s.repo);
      await openForm(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Uno');
      await submit(tester);
      expect(RegExp(r'^[0-9a-f]{32}$').hasMatch(s.repo.progressRequests.single['key'] as String), isTrue);
    });
  });

  group('data refresh', () {
    test('after saving, every cached day is reloaded from the API, not only the one saved', () async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'De ayer', description: 'x');
      final activity = repo.days[formatDate(yesterday)]!.activities.single;
      final container = ProviderContainer(
        retry: noAutomaticRetry,
        overrides: [logbookRepositoryProvider.overrideWithValue(repo)],
      );
      addTearDown(container.dispose);
      // The day where the activity was planned stays on screen (someone is watching it)
      final planned = container.listen(logbookProvider(yesterday), (previous, next) {});
      await container.read(logbookProvider(yesterday).future);
      expect(planned.read().value!.activities.single.status, ActivityStatus.pending);
      final readsBefore = repo.calls.where((c) => c.startsWith('get')).length;

      // The entry is recorded for TODAY, another day
      final saved = container.listen(logbookProvider(today), (previous, next) {});
      await container.read(logbookProvider(today).notifier).registerProgress(
        activityId: activity.id,
        status: ActivityStatus.completed,
        description: 'Terminé',
        key: 'k-1',
      );
      await container.read(logbookProvider(yesterday).future);

      // The planned day was reloaded and now shows the new status
      expect(repo.calls.where((c) => c.startsWith('get')).length, greaterThan(readsBefore + 1));
      expect(planned.read().value!.activities.single.status, ActivityStatus.completed);
      expect(saved.read().value!.progress.single.description, 'Terminé');
    });
  });

  group('responsive', () {
    for (final (name, size) in [('tablet', tablet), ('mobile', mobile)]) {
      testWidgets('the whole flow works on $name without layout errors', (tester) async {
        final s = withActivity();
        await pumpApp(tester, logbook: s.repo, size: size);
        // The dashboard action works at any width, with or without the sidebar
        await tapKey(tester, 'progress-action-${s.activity.id}');
        for (final status in ActivityStatus.values) {
          expect(find.byKey(Key('progress-status-${status.name}')), findsOneWidget);
        }
        await pickStatus(tester, ActivityStatus.blocked);
        await tester.enterText(find.byKey(const Key('progress-reason')), 'Falta el acceso');
        await describe(tester, 'Me detuve');
        await submit(tester);
        expect(s.repo.progressStored(s.activity.id).single.status, ActivityStatus.blocked);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
