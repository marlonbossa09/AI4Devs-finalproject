import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/core/widgets/segmented_control.dart';
import 'package:smartwork/core/widgets/stat_card.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/selected_date.dart';
import 'package:smartwork/features/logbook/presentation/widgets/dashboard_activity_row.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// Main panel (UX-T4): header, indicators, journey state, activities and calendar. What the panel counts and says comes from the
/// logbook the server returned for the selected date; these tests check that it says exactly that and nothing more.

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

final tomorrow = DateTime.utc(2026, 11, 7);
final yesterday = DateTime.utc(2026, 11, 5);

/// A repository whose logbook query waits until the test lets it go (to look at the loading state).
class _SlowLogbookRepository extends FakeLogbookRepository {
  final Completer<void> gate = Completer<void>();

  @override
  Future<LogbookDay?> getLogbook(DateTime date) async {
    await gate.future;
    return super.getLogbook(date);
  }
}

Future<void> pumpApp(
  WidgetTester tester, {
  FakeLogbookRepository? logbook,
  Size size = desktop,
  Role role = Role.collaborator,
  bool settle = true,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
        logbookRepositoryProvider.overrideWithValue(logbook ?? FakeLogbookRepository()),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    await tester.pump();
    await tester.pump();
  }
}

ProviderContainer containerOf(WidgetTester tester) =>
    ProviderScope.containerOf(tester.element(find.byType(SmartworkApp)));

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

Finder statFinder(String label) => find.byWidgetPredicate((w) => w is StatCard && w.label == label);

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

String textOf(WidgetTester tester, String key) => tester.widget<Text>(find.byKey(Key(key))).data!;

String emptyText(WidgetTester tester) =>
    tester.widget<Text>(find.descendant(of: find.byKey(const Key('dashboard-empty')), matching: find.byType(Text))).data!;

Future<void> showOnlyPending(WidgetTester tester) async {
  await tester.tap(find.descendant(of: find.byWidgetPredicate((w) => w is SegmentedControl), matching: find.text('Pendientes')));
  await tester.pumpAndSettle();
}

/// Replaces the day by one that has an UNPLANNED activity and a BLOCKED one with the reason the last progress entry gave.
void seedMixedDay(FakeLogbookRepository repo) {
  repo
    ..seed(today, 'Revisar propuesta', description: 'Leer y comentar')
    ..seed(today, 'Servidor caído', status: ActivityStatus.blocked)
    ..seed(today, 'Entregar informe', status: ActivityStatus.completed);
  final key = formatDate(today);
  final day = repo.days[key]!;
  final blocked = day.activities.firstWhere((a) => a.title == 'Servidor caído');
  final at = DateTime.utc(2026, 11, 6, 16);
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
        createdAt: at,
      ),
    ],
    progress: [
      Progress(
        id: 'pr1',
        activityId: blocked.id,
        date: today,
        status: ActivityStatus.blocked,
        description: 'No responde',
        createdAt: at,
        blockReason: 'Falta el acceso al servidor',
      ),
    ],
  );
}

void main() {
  setUpAll(loadTestFonts);

  group('header', () {
    testWidgets('names the panel, says who it is for and shows the day it is about, with where it stands against today', (tester) async {
      await pumpApp(tester);
      expect(find.text('Mi jornada'), findsOneWidget);
      expect(find.text('Hola, Carlos. Revisa tus actividades y registra tus avances.'), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('dashboard-date')), matching: find.text('Viernes, 6 de noviembre de 2026')), findsOneWidget);
      expect(textOf(tester, 'dashboard-date-relation'), 'Hoy');
    });

    testWidgets('the date follows the day being looked at, and a past or future day says so', (tester) async {
      await pumpApp(tester);
      containerOf(tester).read(selectedDateProvider.notifier).select(tomorrow);
      await tester.pumpAndSettle();
      expect(find.text('Sábado, 7 de noviembre de 2026'), findsOneWidget);
      expect(textOf(tester, 'dashboard-date-relation'), 'Jornada futura');
      containerOf(tester).read(selectedDateProvider.notifier).select(yesterday);
      await tester.pumpAndSettle();
      expect(find.text('Jueves, 5 de noviembre de 2026'), findsOneWidget);
      expect(textOf(tester, 'dashboard-date-relation'), 'Jornada pasada');
    });

    testWidgets('the title is a heading and the date is read as one sentence', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      expect(tester.getSemantics(find.text('Mi jornada')).flagsCollection.isHeader, isTrue);
      expect(tester.getSemantics(find.byKey(const Key('dashboard-date'))).label, 'Fecha laboral: Viernes, 6 de noviembre de 2026, Hoy');
      handle.dispose();
    });

    for (final size in [desktop, tablet, mobile]) {
      testWidgets('${size.width.toInt()} px: there is ONE "Nueva actividad" action and it opens the panel', (tester) async {
        await pumpApp(tester, size: size);
        expect(find.text('Nueva actividad'), findsOneWidget);
        await tapKey(tester, 'dashboard-new-activity');
        expect(find.byKey(const Key('side-panel')), findsOneWidget);
        expect(find.byKey(const Key('plan-title')), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }

    for (final role in Role.values) {
      testWidgets('a ${role.name} sees their own panel, the same way', (tester) async {
        final repo = FakeLogbookRepository()..seed(today, 'Una')..seed(today, 'Dos', status: ActivityStatus.completed);
        await pumpApp(tester, logbook: repo, role: role);
        expect(find.text('Mi jornada'), findsOneWidget);
        expect(stat(tester, 'Total de actividades').value, 2);
        expect(find.byKey(const Key('dashboard-new-activity')), findsOneWidget);
        // The panel only ever asks for the logbook of the person who is signed in
        expect(repo.calls, ['get 2026-11-06']);
      });
    }
  });

  group('indicators', () {
    testWidgets('there are five, in the order of the work, each counting what the server returned', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      await pumpApp(tester, logbook: repo);
      final labels = ['Total de actividades', 'Pendientes', 'En progreso', 'Bloqueadas', 'Completadas'];
      final lefts = [for (final l in labels) tester.getTopLeft(statFinder(l)).dx];
      expect(lefts, orderedEquals([...lefts]..sort())); // left to right in that order
      expect(stat(tester, 'Total de actividades').value, 4);
      expect(stat(tester, 'Pendientes').value, 1);
      expect(stat(tester, 'En progreso').value, 1);
      expect(stat(tester, 'Bloqueadas').value, 1);
      expect(stat(tester, 'Completadas').value, 1);
    });

    testWidgets('they say that the status is the CURRENT one and never show a percentage or a bar', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      await pumpApp(tester, logbook: repo);
      expect(find.text('Estado actual de las actividades de esta jornada'), findsOneWidget);
      expect(find.text('Estado actual'), findsNWidgets(4));
      expect(find.text('En esta jornada'), findsOneWidget);
      expect(find.textContaining('%'), findsNothing);
      expect(find.byType(LinearProgressIndicator), findsNothing);
    });

    testWidgets('on a phone the four status notes are not drawn (the heading above says it once), but are still read by a screen reader', (tester) async {
      final handle = tester.ensureSemantics();
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      await pumpApp(tester, logbook: repo, size: mobile);
      expect(find.text('Estado actual'), findsNothing);
      expect(find.text('Estado actual de las actividades de esta jornada'), findsOneWidget);
      expect(tester.getSemantics(statFinder('Pendientes')).hint, 'Estado actual');
      handle.dispose();
    });

    testWidgets('a planned activity with no progress counts as Pendiente and nothing else', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Solo planificada');
      await pumpApp(tester, logbook: repo);
      expect(stat(tester, 'Pendientes').value, 1);
      expect(stat(tester, 'En progreso').value, 0);
      expect(stat(tester, 'Completadas').value, 0);
    });

    testWidgets('while the day is loading there is no figure (a dash), not a zero that would read as "nothing"', (tester) async {
      final repo = _SlowLogbookRepository();
      await pumpApp(tester, logbook: repo, settle: false);
      expect(stat(tester, 'Total de actividades').value, isNull);
      expect(find.text('–'), findsNWidgets(5));
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      repo.gate.complete();
      await tester.pumpAndSettle();
      expect(stat(tester, 'Total de actividades').value, 0);
      expect(find.text('–'), findsNothing);
    });

    testWidgets('when the day cannot be loaded there is no figure either, and the failure can be retried', (tester) async {
      final repo = FakeLogbookRepository()..getError = const ApiError(code: ApiError.network, message: 'x');
      await pumpApp(tester, logbook: repo);
      expect(stat(tester, 'Total de actividades').value, isNull);
      expect(find.text('–'), findsNWidgets(5));
      expect(find.byKey(const Key('load-error')), findsOneWidget);
      repo.getError = null;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(stat(tester, 'Total de actividades').value, 0);
      expect(find.byKey(const Key('load-error')), findsNothing);
    });

    testWidgets('each card is read as ONE sentence and the summary is a live region that follows the data', (tester) async {
      final handle = tester.ensureSemantics();
      final repo = FakeLogbookRepository()..seed(today, 'Una')..seed(today, 'Dos', status: ActivityStatus.inProgress);
      await pumpApp(tester, logbook: repo);
      final card = tester.getSemantics(statFinder('Pendientes'));
      expect(card.label, 'Pendientes: 1');
      expect(card.hint, 'Estado actual');
      final live = tester.getSemantics(find.byKey(const Key('indicators-scope')));
      expect(live.flagsCollection.isLiveRegion, isTrue);
      expect(
        live.label,
        'Jornada del viernes 6 de noviembre de 2026: 2 actividades. 1 pendiente, 1 en progreso, 0 bloqueadas, 0 completadas.',
      );
      // A new activity is saved: the summary says what the day holds now
      await tapKey(tester, 'dashboard-new-activity');
      await tester.enterText(find.byKey(const Key('plan-title')), 'Tres');
      await tapKey(tester, 'plan-submit');
      expect(tester.getSemantics(find.byKey(const Key('indicators-scope'))).label, contains('3 actividades. 2 pendientes'));
      handle.dispose();
    });

    testWidgets('desktop: all five in one row; tablet: three and two; phone: two columns and the last card takes its own row', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      Offset at(String label) => tester.getTopLeft(statFinder(label));
      await pumpApp(tester, logbook: repo);
      expect(at('Total de actividades').dy, at('Completadas').dy);
      await pumpApp(tester, logbook: repo, size: tablet);
      expect(at('Total de actividades').dy, at('En progreso').dy);
      expect(at('Bloqueadas').dy, greaterThan(at('En progreso').dy));
      expect(at('Bloqueadas').dy, at('Completadas').dy);
      expect(at('Bloqueadas').dx, at('Total de actividades').dx);
      expect(tester.takeException(), isNull);
      await pumpApp(tester, logbook: repo, size: mobile);
      expect(at('Total de actividades').dy, at('Pendientes').dy);
      expect(at('En progreso').dy, at('Bloqueadas').dy);
      expect(at('Completadas').dy, greaterThan(at('En progreso').dy));
      expect(at('Completadas').dx, at('Total de actividades').dx);
      expect(tester.takeException(), isNull);
    });
  });

  group('the day', () {
    testWidgets('an open day says "Abierta", and says it is a state of the day, not of the work', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una', status: ActivityStatus.inProgress);
      await pumpApp(tester, logbook: repo);
      expect(find.descendant(of: find.byKey(const Key('journey-state')), matching: find.text('Abierta')), findsOneWidget);
      expect(textOf(tester, 'journey-text'), 'La jornada está abierta. El cierre se hace desde Mi bitácora.');
      expect(textOf(tester, 'journey-text'), isNot(contains('progreso')));
    });

    testWidgets('a closed day says "Cerrada", since when, and that progress needs it to be reopened; its rows offer no new progress', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      repo.closeDay(today);
      await pumpApp(tester, logbook: repo);
      expect(find.descendant(of: find.byKey(const Key('journey-state')), matching: find.text('Cerrada')), findsOneWidget);
      expect(textOf(tester, 'journey-text'), allOf(contains('La jornada está cerrada desde'), contains('reabrirla desde Mi bitácora')));
      expect(find.textContaining('+ Registrar avance'), findsNothing);
      expect(find.text('Ver detalle'), findsOneWidget); // reading it is still possible
    });

    testWidgets('a day with no logbook says so, neutrally, and says how it is created', (tester) async {
      await pumpApp(tester);
      expect(find.descendant(of: find.byKey(const Key('journey-state')), matching: find.text('Sin bitácora')), findsOneWidget);
      expect(find.text('Abierta'), findsNothing);
      expect(find.text('Cerrada'), findsNothing);
      expect(textOf(tester, 'journey-text'), contains('Todavía no hay bitácora de esta fecha'));
    });

    testWidgets('while it loads or fails it does not claim a state', (tester) async {
      final slow = _SlowLogbookRepository();
      await pumpApp(tester, logbook: slow, settle: false);
      expect(textOf(tester, 'journey-text'), contains('Consultando'));
      expect(find.byKey(const Key('journey-state')), findsNothing);
      slow.gate.complete();
      await tester.pumpAndSettle();
      final failing = FakeLogbookRepository()..getError = const ApiError(code: ApiError.network, message: 'x');
      await pumpApp(tester, logbook: failing);
      expect(textOf(tester, 'journey-text'), contains('No se pudo consultar'));
      expect(find.byKey(const Key('journey-state')), findsNothing);
    });

    testWidgets('it follows the selected day, with its own date told in words', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      await pumpApp(tester, logbook: repo);
      expect(find.text('Fecha laboral: 06/11/2026'), findsOneWidget);
      containerOf(tester).read(selectedDateProvider.notifier).select(yesterday);
      await tester.pumpAndSettle();
      expect(find.text('Fecha laboral: 05/11/2026'), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('journey-state')), matching: find.text('Sin bitácora')), findsOneWidget);
    });
  });

  group('activities', () {
    testWidgets('each row tells its title, how it started, its current status and why it is blocked, all in words', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      await pumpApp(tester, logbook: repo);
      expect(find.text('Revisar propuesta'), findsOneWidget);
      expect(find.text('Leer y comentar'), findsOneWidget);
      expect(find.text('Atender incidente'), findsOneWidget);
      expect(find.text('Registrada sin planificación previa.'), findsOneWidget);
      expect(find.text('No planificada'), findsOneWidget);
      expect(find.text('Planificada'), findsNWidgets(3)); // the other three
      for (final status in ['Pendiente', 'En progreso', 'Bloqueada', 'Completada']) {
        expect(find.descendant(of: find.byType(DashboardActivityRow), matching: find.text(status)), findsWidgets);
      }
      expect(find.text('Motivo del bloqueo: Falta el acceso al servidor'), findsOneWidget);
    });

    testWidgets('a reason is shown only while the activity is still blocked', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      final key = formatDate(today);
      final day = repo.days[key]!;
      repo.days[key] = LogbookDay(
        logbook: day.logbook,
        plannings: day.plannings,
        activities: [
          for (final a in day.activities)
            if (a.title == 'Servidor caído')
              Activity(id: a.id, userId: a.userId, title: a.title, origin: a.origin, status: ActivityStatus.inProgress, date: a.date, createdAt: a.createdAt)
            else
              a,
        ],
        progress: day.progress,
      );
      await pumpApp(tester, logbook: repo);
      expect(find.textContaining('Motivo del bloqueo'), findsNothing);
    });

    testWidgets('no row shows a clock time or a duration, which nothing records for an activity', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      await pumpApp(tester, logbook: repo);
      expect(find.textContaining(RegExp(r'\d{1,2}:\d{2}')), findsNothing);
      expect(find.textContaining(RegExp(r'\d+ ?(min|h)\b')), findsNothing);
      expect(find.textContaining(RegExp(r'(^|\s)hace \d')), findsNothing);
    });

    testWidgets('an activity that is here only because of a planned continuation says so and where it began', (tester) async {
      final repo = FakeLogbookRepository()..seed(yesterday, 'Entrega larga', status: ActivityStatus.inProgress);
      final source = repo.days[formatDate(yesterday)]!;
      final activity = source.activities.single;
      final key = formatDate(today);
      final logbook = (FakeLogbookRepository()..seed(today, 'x')).days[key]!.logbook;
      repo.days[key] = LogbookDay(
        logbook: logbook,
        plannings: [
          Planning(id: 'c1', activityId: activity.id, date: today, type: PlanningType.continuation, description: 'seguir', createdAt: DateTime.utc(2026, 11, 6, 9)),
        ],
        activities: [activity],
      );
      await pumpApp(tester, logbook: repo);
      expect(find.text('Continuación planificada para esta jornada. Origen: 05/11/2026.'), findsOneWidget);
    });

    testWidgets('three clear empty states: no logbook, a logbook with nothing in it, and nothing pending', (tester) async {
      await pumpApp(tester);
      expect(emptyText(tester), contains('Todavía no hay bitácora de esta fecha'));
      final empty = FakeLogbookRepository()..seed(today, 'x');
      empty.days[formatDate(today)] = LogbookDay(logbook: empty.days[formatDate(today)]!.logbook, plannings: const [], activities: const []);
      await pumpApp(tester, logbook: empty);
      expect(emptyText(tester), 'Esta jornada todavía no tiene actividades.');
      final done = FakeLogbookRepository()..seed(today, 'Hecha', status: ActivityStatus.completed);
      await pumpApp(tester, logbook: done);
      await showOnlyPending(tester);
      expect(emptyText(tester), 'No hay actividades pendientes en esta jornada.');
    });

    testWidgets('the existing actions are still there: detail, progress and reactivation', (tester) async {
      final repo = FakeLogbookRepository()
        ..seed(today, 'Abierta')
        ..seed(today, 'Hecha', status: ActivityStatus.completed);
      await pumpApp(tester, logbook: repo);
      final open = repo.days[formatDate(today)]!.activities.firstWhere((a) => a.title == 'Abierta');
      final done = repo.days[formatDate(today)]!.activities.firstWhere((a) => a.title == 'Hecha');
      expect(find.byKey(Key('progress-action-${open.id}')), findsOneWidget);
      expect(find.byKey(Key('reactivation-action-${open.id}')), findsNothing);
      expect(find.byKey(Key('reactivation-action-${done.id}')), findsOneWidget);
      await tapKey(tester, 'activity-open-${open.id}');
      expect(find.byKey(const Key('dashboard-new-activity')), findsNothing); // it left the dashboard for the detail
      expect(find.text('Abierta'), findsWidgets);
    });

    testWidgets('"+ Registrar avance" goes to the progress form of that activity', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Abierta');
      await pumpApp(tester, logbook: repo);
      final id = repo.days[formatDate(today)]!.activities.single.id;
      await tapKey(tester, 'progress-action-$id');
      expect(find.byKey(const Key('dashboard-new-activity')), findsNothing);
      expect(find.text('Registrar avance'), findsWidgets);
    });

    testWidgets('the Pendientes filter still keeps only the pending ones and the footer counts what is in view', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una')..seed(today, 'Hecha', status: ActivityStatus.completed);
      await pumpApp(tester, logbook: repo);
      expect(find.text('2 actividades en esta vista'), findsOneWidget);
      await showOnlyPending(tester);
      expect(find.text('1 actividad en esta vista'), findsOneWidget);
      expect(find.text('Hecha'), findsNothing);
      // The indicators are not a filter: they keep counting the whole day
      expect(stat(tester, 'Completadas').value, 1);
    });
  });

  group('after saving from the panel', () {
    testWidgets('the indicators, the list and the day state refresh, and the selected day does not change', (tester) async {
      final repo = FakeLogbookRepository();
      await pumpApp(tester, logbook: repo);
      expect(find.descendant(of: find.byKey(const Key('journey-state')), matching: find.text('Sin bitácora')), findsOneWidget);
      await tapKey(tester, 'dashboard-new-activity');
      await tester.enterText(find.byKey(const Key('plan-title')), 'Preparar informe');
      await tapKey(tester, 'plan-submit');
      expect(find.byKey(const Key('side-panel')), findsNothing);
      expect(stat(tester, 'Total de actividades').value, 1);
      expect(stat(tester, 'Pendientes').value, 1);
      expect(find.text('Preparar informe'), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('journey-state')), matching: find.text('Abierta')), findsOneWidget);
      expect(containerOf(tester).read(selectedDateProvider), today);
      expect(find.text('Mi jornada'), findsOneWidget); // still on the dashboard
    });
  });

  group('navigation', () {
    testWidgets('"Ver bitácora →" and a day of the calendar both go to Mi bitácora, the second one with that day', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      await pumpApp(tester, logbook: repo);
      await tester.tap(find.text('Ver bitácora →'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('work-date')), findsOneWidget);
      await tester.tap(find.byKey(const Key('nav-dashboard')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('cal-day-10')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('work-date')), findsOneWidget);
      expect(containerOf(tester).read(selectedDateProvider), DateTime.utc(2026, 11, 10));
    });

    testWidgets('the keyboard reaches the main action, then the filter, then the first row\'s actions, in that order', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      await pumpApp(tester, logbook: repo);
      final id = repo.days[formatDate(today)]!.activities.single.id;
      bool inside(String key) {
        var found = false;
        FocusManager.instance.primaryFocus?.context?.visitAncestorElements((e) {
          if (e.widget.key == Key(key)) found = true;
          return !found;
        });
        return found;
      }

      final seen = <String>[];
      for (var i = 0; i < 40 && seen.length < 3; i++) {
        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        for (final key in ['dashboard-new-activity', 'activity-open-$id', 'progress-action-$id']) {
          if (inside(key) && !seen.contains(key)) seen.add(key);
        }
      }
      expect(seen, ['dashboard-new-activity', 'activity-open-$id', 'progress-action-$id']);
    });
  });

  group('responsive', () {
    testWidgets('desktop: the activities sit beside the day state and the calendar', (tester) async {
      final repo = FakeLogbookRepository()..seed(today, 'Una');
      await pumpApp(tester, logbook: repo);
      final activities = tester.getTopLeft(find.text('Actividades de la jornada'));
      final journey = tester.getTopLeft(find.text('Jornada'));
      final calendar = tester.getTopLeft(find.text('Calendario'));
      expect(journey.dx, greaterThan(activities.dx));
      expect(calendar.dx, journey.dx);
      expect(calendar.dy, greaterThan(journey.dy));
      expect(tester.takeException(), isNull);
    });

    for (final size in [tablet, mobile]) {
      testWidgets('${size.width.toInt()} px: the cards stack (day, activities, calendar) with no overflow', (tester) async {
        final repo = FakeLogbookRepository();
        seedMixedDay(repo);
        await pumpApp(tester, logbook: repo, size: size);
        final journey = tester.getTopLeft(find.text('Jornada')).dy;
        final activities = tester.getTopLeft(find.text('Actividades de la jornada')).dy;
        final calendar = tester.getTopLeft(find.text('Calendario')).dy;
        expect(journey, lessThan(activities));
        expect(activities, lessThan(calendar));
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('phone: nothing is wider than the screen and every action has a touch target of at least 40 px', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      await pumpApp(tester, logbook: repo, size: mobile);
      await tester.ensureVisible(find.text('Calendario'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      for (final key in ['dashboard-new-activity']) {
        expect(tester.getSize(find.byKey(Key(key))).height, greaterThanOrEqualTo(40));
      }
      final open = repo.days[formatDate(today)]!.activities.first.id;
      await tester.ensureVisible(find.byKey(Key('activity-open-$open')));
      expect(tester.getSize(find.byKey(Key('activity-open-$open'))).height, greaterThanOrEqualTo(40));
      expect(tester.getSize(find.byKey(Key('progress-action-$open'))).height, greaterThanOrEqualTo(40));
      for (final stat in tester.widgetList<StatCard>(find.byType(StatCard))) {
        expect(stat.label, isNotEmpty);
      }
    });

    testWidgets('a larger text size does not break the panel on a phone', (tester) async {
      final repo = FakeLogbookRepository();
      seedMixedDay(repo);
      tester.platformDispatcher.textScaleFactorTestValue = 1.6;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await pumpApp(tester, logbook: repo, size: mobile);
      expect(tester.takeException(), isNull);
      await tester.drag(find.byType(Scrollable).first, const Offset(0, -3000));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  });
}
