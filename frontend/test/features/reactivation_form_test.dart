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

ProviderContainer containerOf(WidgetTester tester) =>
    ProviderScope.containerOf(tester.element(find.byType(SmartworkApp)));

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

Finder statusPill(Activity activity, String label) =>
    find.descendant(of: find.byKey(Key('status-${activity.id}')), matching: find.text(label));

/// An activity planned on [createdOn] and COMPLETED on [completedOn] by a real progress entry (so the
/// completion exists in its history, as on the server). Returns it as the logbook of [completedOn] shows it.
Future<({FakeLogbookRepository repo, Activity activity})> completed({DateTime? createdOn, DateTime? completedOn}) async {
  final created = createdOn ?? today;
  final done = completedOn ?? today;
  final repo = FakeLogbookRepository()..seed(created, 'Preparar informe', description: 'Revisar cifras');
  final id = repo.days[formatDate(created)]!.activities.single.id;
  await repo.registerProgress(
    activityId: id,
    date: done,
    status: ActivityStatus.completed,
    description: 'Terminada',
    key: 'seed-completion',
  );
  repo.progressRequests.clear();
  repo.calls.clear();
  return (repo: repo, activity: repo.days[formatDate(done)]!.activities.firstWhere((a) => a.id == id));
}

Future<void> openFromLogbook(WidgetTester tester, Activity activity, {DateTime? day}) async {
  if (day != null) containerOf(tester).read(selectedDateProvider.notifier).select(day);
  await tapKey(tester, 'nav-logbook');
  await tapKey(tester, 'reactivation-action-${activity.id}');
}

Future<void> pickStatus(WidgetTester tester, ActivityStatus status) =>
    tapKey(tester, 'reactivation-status-${status.name}');

Future<void> describe(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(const Key('reactivation-description')), text);
}

Future<void> submit(WidgetTester tester) => tapKey(tester, 'reactivation-submit');

void main() {
  setUpAll(loadTestFonts);

  group('the action', () {
    testWidgets('is offered on a Completada activity, in Mi bitácora and in the dashboard', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      expect(find.byKey(Key('reactivation-action-${s.activity.id}')), findsOneWidget); // dashboard
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('reactivation-action-${s.activity.id}')), findsOneWidget); // logbook
    });

    testWidgets('is not offered on an activity that is not Completada', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'Pendiente', status: ActivityStatus.pending)
        ..seed(today, 'En marcha', status: ActivityStatus.inProgress)
        ..seed(today, 'Bloqueada', status: ActivityStatus.blocked);
      await pumpApp(tester, logbook: repo);
      await tapKey(tester, 'nav-logbook');
      expect(find.byWidgetPredicate((w) => w.key.toString().contains('reactivation-action-')), findsNothing);
    });

    testWidgets('is not offered on a Completada activity that was marked as registered by mistake', (tester) async {
      final s = await completed();
      s.repo.markAsError(s.activity.id, reason: 'Duplicada');
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('reactivation-action-${s.activity.id}')), findsNothing);
    });

    testWidgets('opens the form with that activity, already completed, shown and not chosen', (tester) async {
      final s = await completed(createdOn: twoDaysAgo, completedOn: yesterday);
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity, day: yesterday);
      expect(find.text('Reactivar actividad'), findsWidgets);
      expect(find.descendant(of: find.byKey(const Key('reactivation-activity')), matching: find.text('Preparar informe')),
          findsOneWidget);
      expect(statusPillInForm('Completada'), findsOneWidget);
      expect(
        find.textContaining('Completada el ${formatShortDate(yesterday)}'),
        findsOneWidget,
      );
    });

    testWidgets('the activity detail offers it only while the activity is Completada', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-activities');
      await tapKey(tester, 'activity-row-${s.activity.id}');
      expect(find.byKey(const Key('detail-reactivate')), findsOneWidget);
      // An ordinary progress entry stays available: it is a different operation
      expect(find.byKey(const Key('detail-register-progress')), findsOneWidget);

      await tapKey(tester, 'detail-reactivate');
      expect(find.byKey(const Key('reactivation-submit')), findsOneWidget);
    });

    testWidgets('the detail of an activity that is not Completada does not offer it', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'En marcha', status: ActivityStatus.inProgress);
      await pumpApp(tester, logbook: repo);
      await tapKey(tester, 'nav-activities');
      await tapKey(tester, 'activity-row-${repo.days[formatDate(today)]!.activities.single.id}');
      expect(find.byKey(const Key('detail-reactivate')), findsNothing);
    });
  });

  group('the form', () {
    testWidgets('offers the three states that are not Completada, and starts at today with nothing chosen', (tester) async {
      final s = await completed(createdOn: twoDaysAgo, completedOn: yesterday);
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity, day: yesterday);
      for (final status in [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked]) {
        expect(find.byKey(Key('reactivation-status-${status.name}')), findsOneWidget, reason: status.name);
        expect(
          find.descendant(of: find.byKey(Key('reactivation-status-${status.name}')), matching: find.byIcon(Icons.check)),
          findsNothing,
          reason: status.name,
        );
      }
      expect(find.byKey(const Key('reactivation-status-completed')), findsNothing);
      expect(find.text(formatShortDate(today)), findsOneWidget);
      expect(find.byKey(const Key('reactivation-reason')), findsNothing);
      expect(find.byKey(const Key('reactivation-hint')), findsOneWidget);
    });

    testWidgets('the block reason exists only for Bloqueada', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.blocked);
      expect(find.byKey(const Key('reactivation-reason')), findsOneWidget);
      await pickStatus(tester, ActivityStatus.inProgress);
      expect(find.byKey(const Key('reactivation-reason')), findsNothing);
    });

    testWidgets('a stale block reason is never sent once another status is chosen', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.blocked);
      await tester.enterText(find.byKey(const Key('reactivation-reason')), 'Falta acceso');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Sigo adelante');
      await submit(tester);
      expect(s.repo.reactivationRequests.single['blockReason'], isNull);
      expect(s.repo.reactivationRequests.single['status'], ActivityStatus.inProgress);
    });

    testWidgets('sending without anything shows what is missing and sends nothing', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await submit(tester);
      expect(find.text('Elige uno de los tres estados.'), findsOneWidget);
      expect(find.text('Describe cómo retomas la actividad.'), findsOneWidget);
      expect(s.repo.reactivationRequests, isEmpty);
    });

    testWidgets('Bloqueada without a reason, and a description of only spaces, are not sent', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.blocked);
      await describe(tester, '   ');
      await submit(tester);
      expect(find.text('Indica el motivo del bloqueo.'), findsOneWidget);
      expect(find.text('Describe cómo retomas la actividad.'), findsOneWidget);
      expect(s.repo.reactivationRequests, isEmpty);
    });

    testWidgets('cancel goes back without sending anything', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await tapKey(tester, 'reactivation-cancel');
      expect(find.byKey(const Key('reactivation-submit')), findsNothing);
      expect(s.repo.reactivationRequests, isEmpty);
    });

    testWidgets('without a chosen activity it says so, instead of showing an empty form', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      // Reaching the page with no target (e.g. a stale navigation) is handled
      containerOf(tester).read(currentPageProvider.notifier).go(AppPage.reactivation);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('reactivation-none')), findsOneWidget);
      expect(find.byKey(const Key('reactivation-submit')), findsNothing);
    });
  });

  group('reactivating', () {
    testWidgets('sends the contract fields once, and shows the new status everywhere', (tester) async {
      final s = await completed(createdOn: twoDaysAgo, completedOn: yesterday);
      await pumpApp(tester, logbook: s.repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(yesterday);
      await tapKey(tester, 'nav-logbook');
      expect(statusPill(s.activity, 'Completada'), findsOneWidget);
      await tapKey(tester, 'reactivation-action-${s.activity.id}');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, '  Retomo las cifras  ');
      await submit(tester);

      final sent = s.repo.reactivationRequests.single;
      expect(sent['activityId'], s.activity.id);
      expect(sent['date'], formatDate(today));
      expect(sent['status'], ActivityStatus.inProgress);
      expect(sent['description'], 'Retomo las cifras'); // trimmed
      expect(sent['blockReason'], isNull);
      expect((sent['key'] as String).isNotEmpty, isTrue);
      expect(s.repo.progressRequests, isEmpty); // it is NOT an ordinary progress entry

      // Back in Mi bitácora, on the reactivation date, with the new status and the reactivation entry
      expect(find.text('Actividad reactivada.'), findsOneWidget);
      expect(find.byKey(const Key('reactivation-submit')), findsNothing);
      expect(statusPill(s.activity, 'En progreso'), findsOneWidget);
      expect(statusPill(s.activity, 'Completada'), findsNothing);
      final entry = s.repo.progressStored(s.activity.id).last;
      expect(entry.isReactivation, isTrue);
      expect(find.byKey(Key('reactivation-tag-${entry.id}')), findsOneWidget);
      expect(find.textContaining('Reactivación · En progreso: Retomo las cifras'), findsOneWidget);
    });

    testWidgets('the same activity is kept: nothing new is created and the history is preserved', (tester) async {
      final s = await completed(createdOn: twoDaysAgo, completedOn: yesterday);
      final before = s.repo.progressStored(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity, day: yesterday);
      await pickStatus(tester, ActivityStatus.pending);
      await describe(tester, 'Vuelvo a empezar');
      await submit(tester);

      final after = s.repo.progressStored(s.activity.id);
      expect(after.length, before.length + 1);
      expect(after.map((p) => p.id).take(before.length), before.map((p) => p.id)); // untouched, same order
      expect(after.take(before.length).every((p) => !p.isReactivation), isTrue);
      final all = s.repo.days.values.expand((d) => d.activities).map((a) => a.id).toSet();
      expect(all, {s.activity.id}); // no second activity anywhere
    });

    testWidgets('the same date as the completion is valid (CA-187)', (tester) async {
      final s = await completed(); // created and completed today
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Faltaba un detalle');
      await submit(tester);
      expect(s.repo.reactivationRequests.single['date'], formatDate(today));
      expect(statusPill(s.activity, 'En progreso'), findsOneWidget);
    });

    testWidgets('Bloqueada sends its reason and shows it', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.blocked);
      await tester.enterText(find.byKey(const Key('reactivation-reason')), 'Falta acceso');
      await describe(tester, 'Surgió un fallo');
      await submit(tester);
      expect(s.repo.reactivationRequests.single['blockReason'], 'Falta acceso');
      expect(statusPill(s.activity, 'Bloqueada'), findsOneWidget);
      expect(find.text('Motivo del bloqueo: Falta acceso'), findsOneWidget);
    });

    testWidgets('the indicators and the activity list follow the new status', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      expect(stat(tester, 'Completadas').value, 1);
      expect(stat(tester, 'En progreso').value, 0);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Otra vez');
      await submit(tester);

      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Completadas').value, 0);
      expect(stat(tester, 'En progreso').value, 1);

      await tapKey(tester, 'nav-activities');
      expect(find.descendant(of: find.byKey(Key('row-status-${s.activity.id}')), matching: find.text('En progreso')),
          findsOneWidget);
    });

    testWidgets('the open detail shows the reactivation entry, apart from ordinary progress', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-activities');
      await tapKey(tester, 'activity-row-${s.activity.id}');
      await tapKey(tester, 'detail-reactivate');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      await submit(tester);

      // It returns to the detail it came from, already refreshed
      final entry = s.repo.progressStored(s.activity.id).last;
      expect(find.byKey(Key('detail-reactivation-${entry.id}')), findsOneWidget);
      final ordinary = s.repo.progressStored(s.activity.id).first;
      expect(find.byKey(Key('detail-reactivation-${ordinary.id}')), findsNothing);
      expect(find.byKey(const Key('detail-reactivate')), findsNothing); // it is not Completada any more
      expect(find.descendant(of: find.byKey(const Key('detail-status')), matching: find.text('En progreso')), findsOneWidget);
    });

    testWidgets('a continuation can be planned right after reactivating (CA-210), and not before', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsNothing);
      await tapKey(tester, 'reactivation-action-${s.activity.id}');
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      await submit(tester);
      expect(find.byKey(Key('continuation-action-${s.activity.id}')), findsOneWidget);
      expect(find.byKey(Key('reactivation-action-${s.activity.id}')), findsNothing);
    });
  });

  group('double submit and idempotency', () {
    testWidgets('a second tap while the request runs sends nothing, and the button shows it is working', (tester) async {
      final s = await completed();
      s.repo.reactivationGate = Completer<void>();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      final submitFinder = find.byKey(const Key('reactivation-submit'));
      await tester.ensureVisible(submitFinder);
      await tester.tap(submitFinder);
      await tester.pump();
      await tester.tap(submitFinder, warnIfMissed: false);
      await tester.tap(submitFinder, warnIfMissed: false);
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(s.repo.reactivationRequests.length, 1);

      s.repo.reactivationGate!.complete();
      await tester.pumpAndSettle();
      expect(s.repo.reactivationRequests.length, 1);
      expect(s.repo.progressStored(s.activity.id).where((p) => p.isReactivation).length, 1);
    });

    testWidgets('after a failure, retrying the SAME request reuses the key; changing it gets a new one', (tester) async {
      final s = await completed();
      s.repo.reactivationErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      await submit(tester);
      expect(find.byKey(const Key('reactivation-error')), findsOneWidget);
      await submit(tester); // same request, retried
      final keys = s.repo.reactivationRequests.map((r) => r['key']).toList();
      expect(keys.length, 2);
      expect(keys[0], keys[1]);
      expect(s.repo.progressStored(s.activity.id).where((p) => p.isReactivation).length, 1);
    });

    testWidgets('changing what is sent after a failure is a new intention with a new key', (tester) async {
      final s = await completed();
      s.repo.reactivationErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      await submit(tester);
      await describe(tester, 'Retomo de otra forma');
      await submit(tester);
      final keys = s.repo.reactivationRequests.map((r) => r['key']).toList();
      expect(keys[0], isNot(keys[1]));
    });
  });

  group('rejections', () {
    testWidgets('every server rejection shows its own message and keeps the form with what was typed', (tester) async {
      for (final (code, status, message) in [
        ('SECUENCIA_INVALIDA', 409, 'La fecha no puede ser anterior a la de la finalización de la actividad.'),
        ('FECHA_FUTURA_NO_PERMITIDA', 422, 'No se puede registrar ejecución ni cerrar una jornada de fecha futura.'),
        ('ACTIVIDAD_MARCADA_POR_ERROR', 409, 'La actividad está marcada como registrada por error.'),
        ('BITACORA_CERRADA', 409, 'La bitácora de esa fecha está cerrada. Hay que reabrirla antes de modificarla.'),
        ('RECURSO_NO_DISPONIBLE', 404, 'El recurso solicitado no está disponible.'),
      ]) {
        final s = await completed();
        s.repo.reactivationErrors.add(ApiError(code: code, message: 'texto del servidor', status: status));
        await pumpApp(tester, logbook: s.repo);
        await openFromLogbook(tester, s.activity);
        await pickStatus(tester, ActivityStatus.inProgress);
        await describe(tester, 'Retomo');
        await submit(tester);
        expect(tester.widget<Text>(find.byKey(const Key('reactivation-error'))).data, message, reason: code);
        expect(find.byKey(const Key('reactivation-submit')), findsOneWidget, reason: code);
        expect(find.text('Retomo'), findsOneWidget, reason: code);
        expect(find.text('texto del servidor'), findsNothing, reason: code);
        await tester.pumpWidget(const SizedBox());
      }
    });

    testWidgets('when the activity is no longer Completada the screen is reloaded and says so', (tester) async {
      final s = await completed();
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      // Another session reactivated it in the meantime
      s.repo.reactivationErrors.add(const ApiError(code: 'ACTIVIDAD_NO_COMPLETADA', message: 'x', status: 409));
      s.repo.calls.clear();
      await submit(tester);
      expect(
        tester.widget<Text>(find.byKey(const Key('reactivation-error'))).data,
        'La actividad ya no está Completada, así que no hay nada que reactivar. Se ha actualizado su estado.',
      );
      // What the screen believed was stale: the day and the detail it shows are asked for again (the
      // list is invalidated too, and is loaded when its screen is opened)
      expect(s.repo.calls, containsAll(['get ${formatDate(today)}', 'detail ${s.activity.id}']));
    });
  });

  group('closed day', () {
    testWidgets('a closed date is announced and the form cannot be submitted', (tester) async {
      final s = await completed();
      s.repo.closeDay(today);
      await pumpApp(tester, logbook: s.repo);
      await openFromLogbook(tester, s.activity);
      expect(find.text(
          'La jornada del ${formatShortDate(today)} está cerrada, así que no admite nuevos registros. '
          'Elige otra fecha, o reábrela desde Mi bitácora indicando un motivo.'), findsOneWidget);
      await pickStatus(tester, ActivityStatus.inProgress);
      await describe(tester, 'Retomo');
      await tester.ensureVisible(find.byKey(const Key('reactivation-submit')));
      await tester.tap(find.byKey(const Key('reactivation-submit')), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(s.repo.reactivationRequests, isEmpty);
    });
  });

  group('responsive', () {
    for (final (name, size) in [('mobile', mobile), ('tablet', tablet), ('desktop', desktop)]) {
      testWidgets('the whole flow works on $name without layout errors', (tester) async {
        final s = await completed();
        await pumpApp(tester, logbook: s.repo, size: size);
        // The dashboard action works at any width, with or without the sidebar
        await tapKey(tester, 'reactivation-action-${s.activity.id}');
        for (final status in [ActivityStatus.pending, ActivityStatus.inProgress, ActivityStatus.blocked]) {
          expect(find.byKey(Key('reactivation-status-${status.name}')), findsOneWidget);
        }
        await pickStatus(tester, ActivityStatus.blocked);
        await tester.enterText(find.byKey(const Key('reactivation-reason')), 'Falta acceso');
        await describe(tester, 'Retomo la actividad');
        await submit(tester);
        expect(tester.takeException(), isNull);
        expect(s.repo.reactivationRequests.length, 1);
        expect(statusPill(s.activity, 'Bloqueada'), findsOneWidget);
      });
    }
  });
}

Finder statusPillInForm(String label) =>
    find.descendant(of: find.byKey(const Key('reactivation-activity-status')), matching: find.text(label));
