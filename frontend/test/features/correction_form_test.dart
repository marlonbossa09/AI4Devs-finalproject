import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/core/widgets/buttons.dart';
import 'package:smartwork/core/widgets/fields.dart';
import 'package:smartwork/core/widgets/stat_card.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

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

/// An activity planned today with three entries on the same day, in order: En progreso ("Primero"), En progreso
/// ("Segundo") and Completada ("Tercero"). The activity is Completada.
Future<({FakeLogbookRepository repo, Activity activity, List<Progress> entries})> history() async {
  final repo = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
  final activity = repo.days[formatDate(today)]!.activities.single;
  var n = 0;
  for (final (status, text) in [
    (ActivityStatus.inProgress, 'Primero'),
    (ActivityStatus.inProgress, 'Segundo'),
    (ActivityStatus.completed, 'Tercero'),
  ]) {
    await repo.registerProgress(
      activityId: activity.id,
      date: today,
      status: status,
      description: text,
      key: 'seed-${n++}',
    );
  }
  repo.progressRequests.clear();
  repo.calls.clear();
  return (repo: repo, activity: activity, entries: repo.progressStored(activity.id));
}

Future<void> openDetail(WidgetTester tester, Activity activity) async {
  await tapKey(tester, 'nav-activities');
  await tapKey(tester, 'activity-row-${activity.id}');
}

Future<void> openCorrection(WidgetTester tester, Progress entry) => tapKey(tester, 'detail-correct-${entry.id}');

Future<void> describe(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(const Key('correction-description')), text);
  await tester.pump();
}

Future<void> submit(WidgetTester tester) => tapKey(tester, 'correction-submit');

Future<void> confirmChange(WidgetTester tester) => tapKey(tester, 'confirm-discard');

void main() {
  setUpAll(loadTestFonts);

  group('the action in the detail', () {
    testWidgets('every entry of an activity that is not marked offers Corregir', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      for (final entry in s.entries) {
        expect(find.byKey(Key('detail-correct-${entry.id}')), findsOneWidget);
      }
      expect(find.text('Corregir'), findsNWidgets(3));
    });

    testWidgets('the entries of a marked activity offer no correction, and the screen says why', (tester) async {
      final s = await history();
      s.repo.markAsError(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      for (final entry in s.entries) {
        expect(find.byKey(Key('detail-correct-${entry.id}')), findsNothing);
      }
      expect(find.byKey(const Key('detail-correct-blocked')), findsOneWidget);
    });

    testWidgets('a reactivation can be corrected too, and keeps being identified as one', (tester) async {
      final s = await history();
      await s.repo.reactivateActivity(
        activityId: s.activity.id,
        date: today,
        status: ActivityStatus.inProgress,
        description: 'Retomo',
        key: 'seed-react',
      );
      final entries = s.repo.progressStored(s.activity.id);
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      expect(find.byKey(Key('detail-correct-${entries.last.id}')), findsOneWidget);
      await openCorrection(tester, entries.last);
      expect(find.byKey(const Key('correction-reactivation-tag')), findsOneWidget);
      // A reactivation is never Completada
      expect(find.byKey(const Key('correction-status-completed')), findsNothing);
      expect(find.byKey(const Key('correction-status-pending')), findsOneWidget);
    });
  });

  group('the form', () {
    testWidgets('starts as the entry is, shows its work date and cannot change it', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[1]);
      expect(find.text('Corregir avance'), findsWidgets);
      expect(tester.widget<TextField>(find.byKey(const Key('correction-description'))).controller!.text, 'Segundo');
      expect(find.text('Fecha laboral: ${formatShortDate(today)}'), findsOneWidget);
      // There is no field to edit the date or an identifier
      expect(find.byType(DateField), findsNothing);
      expect(find.byKey(const Key('correction-date')), findsOneWidget);
      expect(find.textContaining('no se pueden cambiar'), findsOneWidget);
    });

    testWidgets('offers the four statuses for an ordinary entry, with its own selected', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      for (final status in ActivityStatus.values) {
        expect(find.byKey(Key('correction-status-${status.name}')), findsOneWidget, reason: status.name);
      }
      expect(find.byKey(const Key('correction-reason')), findsNothing); // only for Bloqueada
    });

    testWidgets('Bloqueada shows the reason field; another status hides it again', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await tapKey(tester, 'correction-status-blocked');
      expect(find.byKey(const Key('correction-reason')), findsOneWidget);
      await tapKey(tester, 'correction-status-pending');
      expect(find.byKey(const Key('correction-reason')), findsNothing);
    });

    testWidgets('an unchanged form says there is nothing to correct and sends nothing', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await submit(tester);
      expect(find.byKey(const Key('correction-nothing')), findsOneWidget);
      expect(s.repo.correctionRequests, isEmpty);
    });

    testWidgets('a blank description and a Bloqueada without a reason are explained and send nothing', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, '   ');
      await submit(tester);
      expect(find.text('La descripción no puede quedar vacía.'), findsOneWidget);
      await describe(tester, 'Primero');
      await tapKey(tester, 'correction-status-blocked');
      await submit(tester);
      expect(find.text('Indica el motivo del bloqueo.'), findsOneWidget);
      expect(s.repo.correctionRequests, isEmpty);
    });

    testWidgets('a correction that would leave an entry after a completion is explained before sending', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await tapKey(tester, 'correction-status-completed');
      await submit(tester);
      expect(find.textContaining('posterior a una finalización'), findsOneWidget);
      expect(s.repo.correctionRequests, isEmpty);
    });

    testWidgets('Cancelar goes back to the detail and sends nothing', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, 'Otro texto');
      await tapKey(tester, 'correction-cancel');
      expect(find.byKey(const Key('detail-status')), findsOneWidget);
      expect(s.repo.correctionRequests, isEmpty);
    });
  });

  group('correcting', () {
    testWidgets('a new description is sent alone, with a key; the history shows it as corrected', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, '  Primero, con más detalle  ');
      await submit(tester);

      final sent = s.repo.correctionRequests.single;
      expect(sent['progressId'], s.entries[0].id);
      expect(sent['description'], 'Primero, con más detalle');
      expect(sent['status'], isNull);
      expect(sent['blockReason'], isNull);
      expect((sent['key'] as String).length, 32);
      expect(s.repo.progressRequests, isEmpty); // it is NOT an ordinary progress entry
      // No confirmation: the current status does not change
      expect(find.byKey(const Key('confirm-discard')), findsNothing);
      expect(find.text('Avance corregido.'), findsOneWidget);
      // Back in the detail, reloaded from the server
      expect(find.text('Primero, con más detalle'), findsOneWidget);
      expect(find.byKey(Key('detail-corrected-${s.entries[0].id}')), findsOneWidget);
      expect(find.byKey(Key('detail-corrected-${s.entries[1].id}')), findsNothing);
      // Nothing was created or removed
      expect(s.repo.progressStored(s.activity.id).length, 3);
    });

    testWidgets('changing the status of the last entry asks first, and then updates the current status everywhere', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      expect(stat(tester, 'Completadas').value, 1);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[2]);
      await tapKey(tester, 'correction-status-inProgress');
      await submit(tester);
      // The confirmation names the change of the current status
      expect(find.text('Esta corrección cambia el estado actual'), findsOneWidget);
      expect(find.textContaining('de Completada a En progreso'), findsOneWidget);
      expect(s.repo.correctionRequests, isEmpty);
      await confirmChange(tester);

      expect(s.repo.correctionRequests.single['status'], ActivityStatus.inProgress);
      expect(find.byKey(const Key('detail-status')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('detail-status')), matching: find.text('En progreso')), findsOneWidget);
      // The list, the logbook and the indicators are reloaded from the API
      await tapKey(tester, 'nav-dashboard');
      expect(stat(tester, 'Completadas').value, 0);
      expect(stat(tester, 'En progreso').value, 1);
      await tapKey(tester, 'nav-logbook');
      expect(find.byKey(Key('status-${s.activity.id}')), findsOneWidget);
      expect(find.descendant(of: find.byKey(Key('status-${s.activity.id}')), matching: find.text('En progreso')), findsOneWidget);
    });

    testWidgets('declining the confirmation sends nothing and keeps the form', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[2]);
      await tapKey(tester, 'correction-status-inProgress');
      await submit(tester);
      await tapKey(tester, 'confirm-keep');
      expect(s.repo.correctionRequests, isEmpty);
      expect(find.byKey(const Key('correction-submit')), findsOneWidget);
    });

    testWidgets('changing an entry that is not the last one does not change the current status and asks nothing', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await tapKey(tester, 'correction-status-pending');
      await submit(tester);
      expect(find.byKey(const Key('confirm-discard')), findsNothing);
      expect(s.repo.correctionRequests.single['status'], ActivityStatus.pending);
      expect(find.descendant(of: find.byKey(const Key('detail-status')), matching: find.text('Completada')), findsOneWidget);
    });

    testWidgets('correcting to Bloqueada sends the reason; correcting a block to another status sends no reason', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await tapKey(tester, 'correction-status-blocked');
      await tester.enterText(find.byKey(const Key('correction-reason')), '  Sin acceso  ');
      await submit(tester);
      expect(s.repo.correctionRequests.single['blockReason'], 'Sin acceso');
      expect(find.text('Motivo del bloqueo: Sin acceso'), findsOneWidget);

      await openCorrection(tester, s.entries[0]);
      await tapKey(tester, 'correction-status-inProgress');
      await submit(tester);
      final second = s.repo.correctionRequests.last;
      expect(second['status'], ActivityStatus.inProgress);
      expect(second['blockReason'], isNull);
      expect(find.text('Motivo del bloqueo: Sin acceso'), findsNothing); // the reason was cleared
    });

    testWidgets('a reactivation corrected stays a reactivation', (tester) async {
      final s = await history();
      await s.repo.reactivateActivity(
        activityId: s.activity.id,
        date: today,
        status: ActivityStatus.inProgress,
        description: 'Retomo',
        key: 'seed-react',
      );
      final reactivation = s.repo.progressStored(s.activity.id).last;
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, reactivation);
      await describe(tester, 'Retomo, con más detalle');
      await submit(tester);
      expect(find.byKey(Key('detail-reactivation-${reactivation.id}')), findsOneWidget);
      expect(s.repo.progressStored(s.activity.id).last.isReactivation, isTrue);
    });
  });

  group('rejections', () {
    testWidgets('the server rejecting the sequence is explained and nothing changes', (tester) async {
      final s = await history();
      // The screen believes it is valid; the server disagrees
      s.repo.correctionErrors.add(
        const ApiError(
          code: 'SECUENCIA_INVALIDA',
          message: 'x',
          status: 409,
          details: [
            {'campo': 'estado', 'motivo': 'avance_tras_finalizacion_sin_reactivacion'},
          ],
        ),
      );
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, 'Otro texto');
      await submit(tester);
      expect(find.byKey(const Key('correction-error')), findsOneWidget);
      expect(find.textContaining('posterior a una finalización sin reactivación'), findsOneWidget);
      expect(find.textContaining('No se ha cambiado nada'), findsOneWidget);
      expect(s.repo.progressStored(s.activity.id).first.description, 'Primero');
    });

    testWidgets('an activity marked meanwhile is explained and the screen is refreshed to show the mark', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      s.repo.markAsError(s.activity.id, reason: 'Duplicada'); // marked behind the screen's back
      await describe(tester, 'Otro texto');
      await submit(tester);
      expect(find.text('La actividad está marcada como registrada por error.'), findsOneWidget);
      // Reloaded from the server: the form now explains why it cannot be sent
      expect(find.byKey(const Key('correction-marked')), findsOneWidget);
      expect(tester.widget<FilledButton>(find.descendant(of: find.byKey(const Key('correction-submit')), matching: find.byType(FilledButton))).onPressed, isNull);
    });

    testWidgets('a marked activity cannot be corrected: the form says so and does not send', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      s.repo.markAsError(s.activity.id);
      // Navigating again to the form after the mark shows the notice from the start
      await tapKey(tester, 'correction-cancel');
      await tapKey(tester, 'nav-logbook');
      await tapKey(tester, 'activity-open-${s.activity.id}');
      expect(find.byKey(Key('detail-correct-${s.entries[0].id}')), findsNothing);
    });

    testWidgets('a closed day says it has to be reopened and does not offer to send', (tester) async {
      final s = await history();
      s.repo.closeDay(today);
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      expect(find.byKey(const Key('correction-closed-notice')), findsOneWidget);
      expect(find.textContaining('Reábrela desde Mi bitácora'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.descendant(of: find.byKey(const Key('correction-submit')), matching: find.byType(FilledButton))).onPressed, isNull);
      expect(s.repo.correctionRequests, isEmpty);
    });

    testWidgets('a day closed meanwhile is refused by the server, explained, and the form then shows the notice', (tester) async {
      final s = await history();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      s.repo.closeDay(today); // closed behind the screen's back
      await describe(tester, 'Otro texto');
      await submit(tester);
      expect(find.textContaining('bitácora de esa fecha está cerrada'), findsOneWidget);
      expect(find.byKey(const Key('correction-closed-notice')), findsOneWidget);
    });

    testWidgets('a network failure keeps what was typed and can be retried', (tester) async {
      final s = await history();
      s.repo.correctionErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, 'Otro texto');
      await submit(tester);
      expect(find.byKey(const Key('correction-error')), findsOneWidget);
      expect(tester.widget<TextField>(find.byKey(const Key('correction-description'))).controller!.text, 'Otro texto');
      await submit(tester);
      expect(find.text('Avance corregido.'), findsOneWidget);
    });
  });

  group('one intention, one key (T-04)', () {
    testWidgets('a second tap while the request runs sends nothing, and the form shows it is working', (tester) async {
      final s = await history();
      s.repo.correctionGate = Completer<void>();
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, 'Otro texto');
      final submitFinder = find.byKey(const Key('correction-submit'));
      await tester.ensureVisible(submitFinder);
      await tester.tap(submitFinder);
      await tester.pump();
      await tester.tap(submitFinder, warnIfMissed: false);
      await tester.tap(submitFinder, warnIfMissed: false);
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsWidgets);
      expect(s.repo.correctionRequests.length, 1);
      expect(tester.widget<SecondaryButton>(find.byKey(const Key('correction-cancel'))).onPressed, isNull);

      s.repo.correctionGate!.complete();
      await tester.pumpAndSettle();
      expect(s.repo.correctionRequests.length, 1);
      expect(s.repo.progressStored(s.activity.id).first.description, 'Otro texto');
    });

    testWidgets('after a failure, retrying the SAME correction reuses the key; changing it gets a new one', (tester) async {
      final s = await history();
      s.repo.correctionErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      s.repo.correctionErrors.add(const ApiError(code: ApiError.network, message: 'x', status: 0));
      await pumpApp(tester, logbook: s.repo);
      await openDetail(tester, s.activity);
      await openCorrection(tester, s.entries[0]);
      await describe(tester, 'Otro texto');
      await submit(tester);
      await submit(tester); // the same correction, retried
      await describe(tester, 'Un texto distinto');
      await submit(tester); // another correction
      final keys = s.repo.correctionRequests.map((r) => r['key']).toList();
      expect(keys.length, 3);
      expect(keys[0], keys[1]);
      expect(keys[2], isNot(keys[0]));
    });
  });

  group('every screen size', () {
    for (final (name, size) in [('mobile', mobile), ('tablet', tablet), ('desktop', desktop)]) {
      testWidgets('$name: the whole flow works without layout errors', (tester) async {
        final s = await history();
        await pumpApp(tester, logbook: s.repo, size: size);
        await openDetail(tester, s.activity);
        await openCorrection(tester, s.entries[2]);
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'correction-status-blocked');
        await tester.enterText(find.byKey(const Key('correction-reason')), 'Falta una firma');
        await submit(tester);
        expect(tester.takeException(), isNull);
        await confirmChange(tester);
        expect(find.text('Motivo del bloqueo: Falta una firma'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
