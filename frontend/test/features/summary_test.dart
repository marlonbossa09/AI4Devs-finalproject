import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
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

/// Goes to Mi bitácora (on mobile the sidebar is a drawer opened from the top bar).
Future<void> openLogbook(WidgetTester tester) async {
  if (find.byKey(const Key('menu-toggle')).evaluate().isNotEmpty) {
    await tester.tap(find.byKey(const Key('menu-toggle')));
    await tester.pumpAndSettle();
  }
  await tapKey(tester, 'nav-logbook');
}

Future<void> edit(WidgetTester tester) => tapKey(tester, 'summary-edit');

Future<void> type(WidgetTester tester, String text) async {
  await tester.enterText(find.byKey(const Key('summary-field')), text);
}

Future<void> save(WidgetTester tester) => tapKey(tester, 'summary-save');

String fieldText(WidgetTester tester) => tester.widget<TextField>(find.byKey(const Key('summary-field'))).controller!.text;

/// A repository with a logbook for today (one planned activity) and the given summary.
FakeLogbookRepository withDay({String summary = ''}) {
  final repo = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
  if (summary.isNotEmpty) repo.seedSummary(today, summary);
  return repo;
}

void main() {
  setUpAll(loadTestFonts);

  group('showing the summary', () {
    testWidgets('an empty summary says so and offers to write it', (tester) async {
      await pumpApp(tester, logbook: withDay());
      await openLogbook(tester);
      expect(find.byKey(const Key('summary-empty')), findsOneWidget);
      expect(find.text('Sin resumen'), findsOneWidget);
      expect(find.text('Escribir resumen'), findsOneWidget);
    });

    testWidgets('an existing summary is shown as the server holds it, with the option to edit it', (tester) async {
      await pumpApp(tester, logbook: withDay(summary: 'Revisé el informe y hablé con soporte.'));
      await openLogbook(tester);
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Revisé el informe y hablé con soporte.');
      expect(find.text('Editar resumen'), findsOneWidget);
      expect(find.byKey(const Key('summary-empty')), findsNothing);
    });

    testWidgets('is a block of its own, apart from the activities and their progress', (tester) async {
      final repo = withDay(summary: 'Resumen de la jornada');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      expect(find.text('RESUMEN DIARIO'), findsOneWidget);
      expect(find.text('ACTIVIDADES Y AVANCES'), findsOneWidget);
      expect(find.textContaining('No es una actividad ni un avance'), findsOneWidget);
      // Each thing lives in its own place: the summary is not among the activities, nor the reverse
      final section = find.byKey(const Key('summary-section'));
      expect(find.descendant(of: section, matching: find.text('Preparar informe')), findsNothing);
      expect(find.descendant(of: section, matching: find.text('Resumen de la jornada')), findsOneWidget);
      // The summary comes before the activities heading
      expect(tester.getTopLeft(section).dy, lessThan(tester.getTopLeft(find.byKey(const Key('activities-heading'))).dy));
      expect(tester.getTopLeft(find.byKey(const Key('activities-heading'))).dy,
          lessThan(tester.getTopLeft(find.text('Preparar informe')).dy));
    });

    testWidgets('a summary does not disturb the activities, their progress or the indicators', (tester) async {
      final repo = withDay(summary: 'Algo de texto');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      final activity = repo.days[formatDate(today)]!.activities.single;
      expect(find.byKey(Key('activity-${activity.id}')), findsOneWidget);
      expect(find.byKey(Key('progress-action-${activity.id}')), findsOneWidget);
    });
  });

  group('writing and updating', () {
    testWidgets('writes a summary through the API and shows what the server holds afterwards', (tester) async {
      final repo = withDay();
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      expect(find.byKey(const Key('summary-field')), findsOneWidget);
      await type(tester, 'Hoy cerré el informe y atendí una llamada.');
      await save(tester);
      expect(repo.summaryRequests.single, {'date': '2026-11-06', 'summary': 'Hoy cerré el informe y atendí una llamada.'});
      expect(find.text('Resumen guardado.'), findsOneWidget);
      expect(find.byKey(const Key('summary-field')), findsNothing); // back to reading
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Hoy cerré el informe y atendí una llamada.');
      expect(repo.days[formatDate(today)]!.logbook.summary, 'Hoy cerré el informe y atendí una llamada.');
    });

    testWidgets('the modification moment shown is the one the server returned', (tester) async {
      final repo = withDay();
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      final before = repo.days[formatDate(today)]!.logbook.updatedAt;
      expect(find.text(formatDateTime(before)), findsWidgets);
      await edit(tester);
      await type(tester, 'Nuevo');
      await save(tester);
      final after = repo.days[formatDate(today)]!.logbook.updatedAt;
      expect(after.isAfter(before), isTrue);
      expect(find.text(formatDateTime(after)), findsOneWidget); // the "Modificada" date moved
    });

    testWidgets('updating replaces the previous text, and the editor starts from it', (tester) async {
      final repo = withDay(summary: 'Primera versión');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      expect(fieldText(tester), 'Primera versión');
      await type(tester, 'Segunda versión');
      await save(tester);
      expect(repo.summaryRequests.single['summary'], 'Segunda versión');
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Segunda versión');
    });

    testWidgets('the text goes exactly as typed, spaces and line breaks included', (tester) async {
      final repo = withDay();
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, '  Línea 1\nLínea 2  ');
      await save(tester);
      expect(repo.summaryRequests.single['summary'], '  Línea 1\nLínea 2  ');
    });

    testWidgets('an empty summary is valid: it can be saved, and clears the text', (tester) async {
      final repo = withDay(summary: 'Se va a borrar');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, '');
      await save(tester);
      expect(repo.summaryRequests.single['summary'], '');
      expect(find.byKey(const Key('summary-empty')), findsOneWidget);
      expect(find.text('Escribir resumen'), findsOneWidget);
    });

    testWidgets('saving without changes is also allowed (it renews the modification date)', (tester) async {
      final repo = withDay(summary: 'Igual');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await save(tester);
      expect(repo.summaryRequests.single['summary'], 'Igual');
    });

    testWidgets('cancelling discards what was typed (after confirming it) and sends nothing', (tester) async {
      final repo = withDay(summary: 'Original');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Algo que no se guarda');
      await tapKey(tester, 'summary-cancel');
      await tapKey(tester, 'confirm-discard'); // typed text is not thrown away without asking
      expect(repo.summaryRequests, isEmpty);
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Original');
      await edit(tester);
      expect(fieldText(tester), 'Original'); // the discarded text did not come back
    });

    testWidgets('saving reloads the day from the API, and what was saved is still there after leaving and coming back', (tester) async {
      final repo = withDay();
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      final readsBefore = repo.calls.where((c) => c.startsWith('get ')).length;
      await edit(tester);
      await type(tester, 'Persistido');
      await save(tester);
      // What is on screen was read back from the server, not assumed by the client
      expect(repo.calls.where((c) => c.startsWith('get ')).length, greaterThan(readsBefore));
      await tapKey(tester, 'nav-dashboard');
      await tapKey(tester, 'nav-logbook');
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Persistido');
    });
  });

  group('while it is saving', () {
    testWidgets('shows the loading state, disables the editor and ignores a second tap', (tester) async {
      final repo = withDay();
      repo.summaryGate = Completer<void>();
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Texto');
      await tester.ensureVisible(find.byKey(const Key('summary-save')));
      await tester.tap(find.byKey(const Key('summary-save')));
      await tester.pump();
      expect(
        find.descendant(of: find.byKey(const Key('summary-save')), matching: find.byType(CircularProgressIndicator)),
        findsOneWidget,
      );
      expect(tester.widget<TextField>(find.byKey(const Key('summary-field'))).enabled, isFalse);
      expect(
        tester.widget<OutlinedButton>(find.descendant(of: find.byKey(const Key('summary-cancel')), matching: find.byType(OutlinedButton))).onPressed,
        isNull,
      );
      await tester.tap(find.byKey(const Key('summary-save')), warnIfMissed: false);
      await tester.pump();
      await tester.tap(find.byKey(const Key('summary-save')), warnIfMissed: false);
      await tester.pump();
      expect(repo.summaryRequests, hasLength(1));
      repo.summaryGate!.complete();
      await tester.pumpAndSettle();
      expect(repo.summaryRequests, hasLength(1));
      expect(find.text('Resumen guardado.'), findsOneWidget);
    });
  });

  group('server errors', () {
    final cases = <(String, int, String)>[
      ('FECHA_NO_CUBIERTA', 422, 'Esa fecha no está cubierta por tu pertenencia a un equipo.'),
      ('SOLICITUD_INVALIDA', 400, 'La solicitud no es válida.'),
      ('ACCESO_DESACTIVADO', 403, 'Tu acceso está desactivado. Contacta con quien administra el servicio.'),
      ('SIN_PERTENENCIA_VIGENTE', 403, 'No tienes una pertenencia vigente a un equipo.'),
    ];
    for (final (code, status, message) in cases) {
      testWidgets('$code is explained and the typed text is kept', (tester) async {
        final repo = withDay();
        repo.summaryErrors.add(ApiError(code: code, message: 'x', status: status));
        await pumpApp(tester, logbook: repo);
        await openLogbook(tester);
        await edit(tester);
        await type(tester, 'No quiero perder esto');
        await save(tester);
        expect(tester.widget<Text>(find.byKey(const Key('summary-error'))).data, message);
        expect(fieldText(tester), 'No quiero perder esto');
        expect(tester.widget<TextField>(find.byKey(const Key('summary-field'))).enabled, isTrue); // can retry
        expect(repo.days[formatDate(today)]!.logbook.summary, isEmpty); // nothing was saved
      });
    }

    testWidgets('a text that is too long is explained with the server maximum', (tester) async {
      final repo = withDay();
      repo.summaryErrors.add(const ApiError(
        code: 'TEXTO_DEMASIADO_LARGO',
        message: 'x',
        status: 422,
        details: [
          {'campo': 'resumen', 'maximo': 8000},
        ],
      ));
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'x' * 50);
      await save(tester);
      expect(tester.widget<Text>(find.byKey(const Key('summary-error'))).data, 'El texto supera el máximo permitido (8000 caracteres).');
    });

    testWidgets('a network failure keeps the text and can be retried', (tester) async {
      final repo = withDay();
      repo.summaryErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Reintento');
      await save(tester);
      expect(find.textContaining('No se pudo conectar con el servidor'), findsOneWidget);
      await save(tester);
      expect(find.byKey(const Key('summary-error')), findsNothing);
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Reintento');
      expect(repo.summaryRequests, hasLength(2));
    });

    testWidgets('an expired session sends the user back to the login', (tester) async {
      final repo = withDay();
      repo.summaryErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'x');
      await save(tester);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });

    testWidgets('a day closed meanwhile is detected: the editor goes away and the reason is shown', (tester) async {
      final repo = withDay(summary: 'Texto');
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Cambio que llega tarde');
      repo.closeDay(today); // closed from another session while this screen was editing
      await save(tester);
      expect(find.byKey(const Key('summary-field')), findsNothing);
      expect(find.byKey(const Key('summary-closed-note')), findsOneWidget);
      expect(find.byKey(const Key('summary-edit')), findsNothing);
      expect(find.text('Cerrada'), findsOneWidget); // the header was reloaded too
      expect(repo.days[formatDate(today)]!.logbook.summary, 'Texto'); // unchanged
    });
  });

  group('closed day', () {
    testWidgets('shows the summary but offers no editing, and says how to change it', (tester) async {
      final repo = withDay(summary: 'Resumen de una jornada cerrada');
      repo.closeDay(today);
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Resumen de una jornada cerrada');
      expect(find.byKey(const Key('summary-edit')), findsNothing);
      expect(find.byKey(const Key('summary-closed-note')), findsOneWidget);
      expect(
        find.descendant(of: find.byKey(const Key('summary-closed-note')), matching: find.textContaining('hay que reabrirla')),
        findsOneWidget,
      );
      expect(repo.summaryRequests, isEmpty);
    });

    testWidgets('an empty closed day does not offer to write the summary either', (tester) async {
      final repo = withDay();
      repo.closeDay(today);
      await pumpApp(tester, logbook: repo);
      await openLogbook(tester);
      expect(find.byKey(const Key('summary-empty')), findsOneWidget);
      expect(find.text('Escribir resumen'), findsNothing);
    });
  });

  group('other days', () {
    testWidgets('a past day can be edited too', (tester) async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'De ayer');
      await pumpApp(tester, logbook: repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(yesterday);
      await tester.pumpAndSettle();
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Corrección de ayer');
      await save(tester);
      expect(repo.summaryRequests.single, {'date': '2026-11-05', 'summary': 'Corrección de ayer'});
    });

    testWidgets('a future day can be edited too (the contract allows it)', (tester) async {
      final repo = FakeLogbookRepository()..seed(tomorrow, 'De mañana');
      await pumpApp(tester, logbook: repo);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Notas para mañana');
      await save(tester);
      expect(repo.summaryRequests.single['date'], '2026-11-07');
    });

    testWidgets('changing the date while editing starts the other day with a fresh, closed editor', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'De hoy')
        ..seed(yesterday, 'De ayer')
        ..seedSummary(yesterday, 'Resumen de ayer');
      await pumpApp(tester, logbook: repo);
      // The other day is already loaded (alive in the cache), so switching to it does not even show a
      // loading frame: only the per-logbook key stops the open editor from following the user
      final cached = containerOf(tester).listen(logbookProvider(yesterday), (previous, next) {});
      addTearDown(cached.close);
      await containerOf(tester).read(logbookProvider(yesterday).future);
      await openLogbook(tester);
      await edit(tester);
      await type(tester, 'Texto a medias de hoy');
      containerOf(tester).read(selectedDateProvider.notifier).select(yesterday);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('summary-field')), findsNothing); // the editor did not follow to the other day
      expect(tester.widget<Text>(find.byKey(const Key('summary-text'))).data, 'Resumen de ayer');
      expect(repo.summaryRequests, isEmpty); // and nothing was sent
    });

    testWidgets('a date without logbook still asks to open it first', (tester) async {
      await pumpApp(tester, logbook: FakeLogbookRepository());
      await openLogbook(tester);
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
      expect(find.byKey(const Key('summary-section')), findsNothing);
    });
  });

  group('responsive', () {
    for (final (name, size) in [('tablet', tablet), ('mobile', mobile)]) {
      testWidgets('writing and saving works on $name without layout errors', (tester) async {
        final repo = withDay(summary: 'Un resumen bastante largo para comprobar el ajuste de texto en pantallas estrechas ' * 3);
        await pumpApp(tester, logbook: repo, size: size);
        await openLogbook(tester);
        expect(tester.takeException(), isNull);
        await edit(tester);
        expect(tester.takeException(), isNull);
        await type(tester, 'Nuevo texto ' * 40);
        if (size == mobile) {
          // On a phone the actions are stacked and full width
          final width = tester.getSize(find.byKey(const Key('summary-save'))).width;
          expect(width, greaterThan(250));
        }
        await save(tester);
        expect(repo.summaryRequests, hasLength(1));
        expect(find.byKey(const Key('summary-text')), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
