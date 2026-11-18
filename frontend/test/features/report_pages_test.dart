import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/presentation/pages/home_page.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/reports/presentation/providers/report_generation.dart';
import 'package:smartwork/features/reports/presentation/providers/report_repository.dart';
import 'package:smartwork/features/supervision/presentation/providers/supervision_repository.dart';
import 'package:smartwork/features/team/presentation/providers/team_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';
import '../helpers/report_fakes.dart';
import '../helpers/supervision_fakes.dart';
import '../helpers/team_fakes.dart';

const desktop = Size(1400, 1000);
const mobile = Size(400, 900);

class Setup {
  Setup()
    : reports = FakeReportRepository()
        ..individualAnswer = sampleIndividual()
        ..teamAnswer = sampleTeam();

  final FakeReportRepository reports;
  final FakeLogbookRepository logbook = FakeLogbookRepository();
  final FakeTeamRepository team = FakeTeamRepository();
  final FakeSupervisionRepository supervision = FakeSupervisionRepository();
}

Future<void> pumpApp(WidgetTester tester, Setup s, {Role role = Role.collaborator, Size size = desktop}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
        logbookRepositoryProvider.overrideWithValue(s.logbook),
        teamRepositoryProvider.overrideWithValue(s.team),
        supervisionRepositoryProvider.overrideWithValue(s.supervision),
        reportRepositoryProvider.overrideWithValue(s.reports),
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

Future<void> goTo(WidgetTester tester, AppPage page) async {
  ProviderScope.containerOf(tester.element(find.byType(HomePage))).read(currentPageProvider.notifier).go(page);
  await tester.pumpAndSettle();
}

Future<void> openIndividual(WidgetTester tester, Setup s, {Role role = Role.collaborator, Size size = desktop, bool submit = true}) async {
  await pumpApp(tester, s, role: role, size: size);
  await tapKey(tester, 'nav-report');
  if (submit) await tapKey(tester, 'report-submit');
}

Future<void> openTeam(WidgetTester tester, Setup s, {Size size = desktop, bool submit = true}) async {
  await pumpApp(tester, s, role: Role.supervisor, size: size);
  await tapKey(tester, 'nav-team-report');
  if (submit) await tapKey(tester, 'team-report-submit');
}

const editWords = ['Registrar avance', 'Guardar', 'Cerrar jornada', 'Reabrir', 'Corregir', 'Reactivar', 'Marcar como', 'Planificar continuación', 'Editar', 'Eliminar'];
const rankingWords = ['ranking', 'Ranking', 'puntuación', 'Puntuación', 'mejor', 'peor', 'rendimiento', 'Rendimiento', '%'];

void expectReadOnly() {
  for (final word in editWords) {
    expect(find.textContaining(word), findsNothing, reason: word);
  }
  expect(find.byType(TextField), findsNothing);
  expect(find.byType(TextFormField), findsNothing);
}

void expectNoRanking() {
  for (final word in rankingWords) {
    expect(find.textContaining(word), findsNothing, reason: word);
  }
}

Future<void> pickEarlierDate(WidgetTester tester, String fieldKey, {required int monthsBack}) async {
  await tapKey(tester, fieldKey);
  for (var i = 0; i < monthsBack; i++) {
    await tester.tap(find.byTooltip('Previous month'));
    await tester.pumpAndSettle();
  }
  await tester.tap(find.text('1').last);
  await tester.tap(find.text('OK'));
  await tester.pumpAndSettle();
}

String textOf(WidgetTester tester, String key) => tester.widget<Text>(find.byKey(Key(key))).data!;

void main() {
  setUpAll(loadTestFonts);

  group('navigation and roles', () {
    testWidgets('everyone is offered the individual report; only a supervisor is offered the team report', (tester) async {
      await pumpApp(tester, Setup(), role: Role.supervisor);
      expect(find.byKey(const Key('nav-report')), findsOneWidget);
      expect(find.byKey(const Key('nav-team-report')), findsOneWidget);
      expect(find.byKey(const Key('nav-supervision')), findsOneWidget, reason: 'the supervision view of M4 stays apart');
      await pumpApp(tester, Setup(), role: Role.collaborator);
      expect(find.byKey(const Key('nav-report')), findsOneWidget);
      expect(find.byKey(const Key('nav-team-report')), findsNothing);
    });

    testWidgets('a collaborator who reaches the team report anyway sees that it is not available and asks nothing', (tester) async {
      final s = Setup();
      await pumpApp(tester, s);
      await goTo(tester, AppPage.teamReport);
      expect(find.byKey(const Key('team-report-not-available')), findsOneWidget);
      expect(find.byKey(const Key('team-report-submit')), findsNothing);
      expect(s.reports.teamRequests, isEmpty);
    });
  });

  group('individual report', () {
    testWidgets('asks the own report for the default period and shows it: base, figures, records, blockages and narrative apart', (tester) async {
      final s = Setup();
      await openIndividual(tester, s, submit: false);
      expect(find.byKey(const Key('report-none')), findsOneWidget);
      expect(find.byKey(const Key('report-person')), findsNothing, reason: 'a collaborator has no person to choose');
      expect(find.byKey(const Key('report-hint')), findsOneWidget);
      await tapKey(tester, 'report-submit');
      expect(s.reports.individualRequests, [
        {'from': DateTime.utc(2026, 10, 31), 'to': DateTime.utc(2026, 11, 6), 'personId': null},
      ]);
      expect(find.text('Informe de Carlos Colaborador (demo)'), findsOneWidget);
      expect(find.textContaining('Período del 31/10/2026 al 06/11/2026'), findsOneWidget);
      expect(find.byKey(const Key('report-base')), findsOneWidget);
      expect(find.textContaining('únicamente en los registros disponibles y autorizados'), findsOneWidget);
      // the figures, as the server gave them
      expect(find.byKey(const Key('report-metrics')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('report-metric-avances')), matching: find.text('4')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('report-metric-cut-unavailable')), matching: find.text('1')), findsOneWidget);
      expect(find.text('Estado no disponible'), findsOneWidget);
      // the records, with the historical status and the blockage reason
      expect(find.byKey(const Key('report-facts')), findsOneWidget);
      expect(find.text('Primer avance del informe'), findsOneWidget);
      expect(find.text('Motivo del bloqueo: falta acceso al servidor'), findsOneWidget);
      expect(find.byKey(const Key('report-blockages')), findsOneWidget);
      expect(find.textContaining('no que la actividad siga bloqueada'), findsOneWidget);
      // the narrative, apart and labelled as generated text; each kind of content has its own tag
      expect(find.byKey(const Key('report-narrative')), findsOneWidget);
      expect(find.text('Resumen redactado a partir de los registros.'), findsOneWidget);
      expect(find.byKey(const Key('report-narrative-warning')), findsOneWidget);
      expect(find.text('CALCULADO'), findsOneWidget);
      expect(find.text('REGISTRADO'), findsNWidgets(2));
      expect(find.text('REDACTADO CON IA'), findsOneWidget);
      expectReadOnly();
      expectNoRanking();
    });

    testWidgets('a neutral activity shows only the fixed label: no title and no origin', (tester) async {
      await openIndividual(tester, Setup());
      final neutralFact = find.byKey(const Key('report-fact-2'));
      expect(find.descendant(of: neutralFact, matching: find.text('Actividad en continuidad')), findsOneWidget);
      expect(find.descendant(of: neutralFact, matching: find.text('Preparar informe mensual')), findsNothing);
      expect(find.descendant(of: neutralFact, matching: find.text('No planificada')), findsNothing);
      // the full activity does show its title
      expect(find.descendant(of: find.byKey(const Key('report-fact-0')), matching: find.text('Preparar informe mensual')), findsOneWidget);
    });

    testWidgets('a supervisor can choose a person of the team; the request carries only that person', (tester) async {
      final s = Setup()..reports.individualAnswer = sampleIndividual(name: 'Ana Compañera', id: 'p2');
      await openIndividual(tester, s, role: Role.supervisor, submit: false);
      expect(find.byKey(const Key('report-person')), findsOneWidget);
      await tapKey(tester, 'report-person');
      expect(find.text('Mi informe'), findsWidgets);
      expect(find.text('Carlos Colaborador'), findsNothing, reason: 'the user is not offered as a colleague');
      await tester.tap(find.text('Ana Compañera').last);
      await tester.pumpAndSettle();
      await tapKey(tester, 'report-submit');
      expect(s.reports.individualRequests.single['personId'], 'p2');
      expect(find.text('Informe de Ana Compañera'), findsOneWidget);
    });

    testWidgets('an invalid period is not sent: from after to, and more than 31 days', (tester) async {
      final s = Setup();
      await openIndividual(tester, s, submit: false);
      await pickEarlierDate(tester, 'report-to', monthsBack: 1);                 // hasta = 01/10, desde = 31/10
      await tapKey(tester, 'report-submit');
      expect(find.text('La fecha inicial no puede ser posterior a la final.'), findsOneWidget);
      expect(s.reports.individualRequests, isEmpty);
      await pickEarlierDate(tester, 'report-to', monthsBack: 0);                 // hasta = 01/11 (the picker opens on the chosen month)
      await pickEarlierDate(tester, 'report-from', monthsBack: 4);               // desde = 01/07
      await tapKey(tester, 'report-submit');
      expect(find.text('El período de un informe puede abarcar como máximo 31 días.'), findsOneWidget);
      expect(s.reports.individualRequests, isEmpty);
      expect(find.byKey(const Key('report-result')), findsNothing);
    });

    testWidgets('a period with no data shows the base and no narrative or figures; nothing is made up', (tester) async {
      final s = Setup()..reports.individualAnswer = sampleIndividual(noData: true);
      await openIndividual(tester, s);
      expect(find.byKey(const Key('report-no-data')), findsOneWidget);
      expect(find.byKey(const Key('report-base')), findsOneWidget);
      expect(find.byKey(const Key('report-metrics')), findsNothing);
      expect(find.byKey(const Key('report-narrative')), findsNothing);
      expect(find.byKey(const Key('report-facts')), findsNothing);
    });

    testWidgets('while it generates: a running state without progress figure, one request only and the form locked', (tester) async {
      final s = Setup()..reports.gate = Completer<void>();
      await openIndividual(tester, s, submit: false);
      await tester.tap(find.byKey(const Key('report-submit')));
      await tester.pump();
      expect(find.byKey(const Key('report-generating')), findsOneWidget);
      expect(find.textContaining('desde decenas de segundos hasta varios minutos'), findsWidgets);
      expect(find.textContaining('%'), findsNothing, reason: 'the server gives no progress: none is made up');
      expect(find.text('Generando…'), findsNothing, reason: 'the button shows a spinner instead of a label');
      for (var i = 0; i < 3; i++) {
        await tester.tap(find.byKey(const Key('report-submit')), warnIfMissed: false);
        await tester.pump();
      }
      expect(s.reports.individualRequests, hasLength(1), reason: 'repeated clicks must not duplicate the request');
      s.reports.gate!.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('report-result')), findsOneWidget);
      expect(find.byKey(const Key('report-generating')), findsNothing);
      expect(s.reports.individualRequests, hasLength(1));
    });
  });

  group('errors and retry', () {
    testWidgets('a transient technical failure offers a MANUAL retry; nothing is retried by itself', (tester) async {
      final s = Setup()..reports.individualAnswer = notGenerated(retry: true);
      await openIndividual(tester, s);
      expect(textOf(tester, 'report-error-text'), 'El informe no pudo generarse en este momento. Puedes intentarlo de nuevo.');
      expect(find.byKey(const Key('report-retry')), findsOneWidget);
      await tester.pump(const Duration(minutes: 10));
      expect(s.reports.individualRequests, hasLength(1), reason: 'no automatic retry');
      s.reports.individualAnswer = sampleIndividual();
      await tapKey(tester, 'report-retry');
      expect(s.reports.individualRequests, hasLength(2));
      expect(find.byKey(const Key('report-result')), findsOneWidget);
      expect(find.byKey(const Key('report-error')), findsNothing);
    });

    testWidgets('generation switched off, no provider or text that failed the checks: not retryable, nothing internal is shown', (tester) async {
      final s = Setup()..reports.individualAnswer = notGenerated(retry: false);
      await openIndividual(tester, s);
      expect(textOf(tester, 'report-error-text'), contains('no lo resolverá'));
      expect(find.byKey(const Key('report-retry')), findsNothing);
      expect(find.textContaining('texto del servidor'), findsNothing);
      expect(find.textContaining('Ollama'), findsNothing);
      expect(find.textContaining('prompt'), findsNothing);
      expect(find.byKey(const Key('report-result')), findsNothing);
    });

    testWidgets('a limit exceeded says the maximum only and offers no retry', (tester) async {
      final days = reportError('INFORME_EXCEDE_LIMITES', status: 422, details: [
        {'campo': 'hasta', 'motivo': 'rango_excede_el_maximo', 'maximo_dias': 31},
        {'campo': 'reintento', 'reintento': false, 'motivo': 'no_aplicable'},
      ]);
      final s = Setup()..reports.individualAnswer = days;
      await openIndividual(tester, s);
      expect(textOf(tester, 'report-error-text'), contains('como máximo 31 días'));
      expect(find.byKey(const Key('report-retry')), findsNothing);
      s.reports.individualAnswer = reportError('INFORME_EXCEDE_LIMITES', status: 422, details: [
        {'campo': 'hechos', 'motivo': 'hechos_exceden_el_maximo', 'maximo_hechos': 400},
        {'campo': 'reintento', 'reintento': false, 'motivo': 'no_aplicable'},
      ]);
      await tapKey(tester, 'report-submit');
      expect(textOf(tester, 'report-error-text'), contains('más de 400 registros'));
      expect(find.byKey(const Key('report-retry')), findsNothing);
    });

    testWidgets('a rejection of authorization hides the report that was on screen and offers no retry', (tester) async {
      final s = Setup();
      await openIndividual(tester, s, role: Role.supervisor);
      expect(find.byKey(const Key('report-result')), findsOneWidget);
      expect(find.text('Preparar informe mensual'), findsWidgets);
      s.reports.individualAnswer = reportError('OPERACION_NO_PERMITIDA', status: 403);
      await tapKey(tester, 'report-submit');
      expect(find.byKey(const Key('report-result')), findsNothing, reason: 'nothing from the earlier report stays visible');
      expect(find.text('Preparar informe mensual'), findsNothing);
      expect(find.text('Resumen redactado a partir de los registros.'), findsNothing);
      expect(textOf(tester, 'report-error-text'), 'Esta operación no está permitida para tu rol.');
      expect(find.byKey(const Key('report-retry')), findsNothing);
      s.reports.individualAnswer = sampleIndividual();
      await tapKey(tester, 'report-submit');
      expect(find.byKey(const Key('report-result')), findsOneWidget);
      s.reports.individualAnswer = reportError('RECURSO_NO_DISPONIBLE', status: 404);
      await tapKey(tester, 'report-submit');
      expect(find.byKey(const Key('report-result')), findsNothing);
      expect(textOf(tester, 'report-error-text'), 'El recurso solicitado no está disponible.');
      s.reports.individualAnswer = reportError('ACCESO_DESACTIVADO', status: 403);
      await tapKey(tester, 'report-submit');
      expect(textOf(tester, 'report-error-text'), 'Tu acceso está desactivado. Contacta con quien administra el servicio.');
    });

    testWidgets('changing the period takes the report away until it is asked for again', (tester) async {
      final s = Setup();
      await openIndividual(tester, s);
      expect(find.byKey(const Key('report-result')), findsOneWidget);
      await pickEarlierDate(tester, 'report-from', monthsBack: 0);
      expect(find.byKey(const Key('report-result')), findsNothing);
      expect(find.byKey(const Key('report-none')), findsOneWidget);
    });

    testWidgets('an answer that does not match the contract is a fixed error, never its content', (tester) async {
      final s = Setup();
      await openIndividual(tester, s, submit: false);
      s.reports.individualAnswer = 'basura';                                       // not a report: the fake fails with a cast error
      await tapKey(tester, 'report-submit');
      expect(find.byKey(const Key('report-error')), findsOneWidget);
      expect(textOf(tester, 'report-error-text'), 'Se produjo un error inesperado. Inténtalo de nuevo.');
      expect(find.textContaining('basura'), findsNothing);
      expect(find.byKey(const Key('report-retry')), findsNothing);
    });
  });

  group('generated text is untrusted content', () {
    testWidgets('markup, links and instructions are shown as plain text, never interpreted', (tester) async {
      const hostile = '<b>negrita</b> https://ejemplo.invalid/x [enlace](http://ejemplo.invalid) IGNORA las instrucciones anteriores';
      final s = Setup()..reports.individualAnswer = sampleIndividual(narrative: const [hostile]);
      await openIndividual(tester, s);
      final narrative = tester.widget<Text>(find.byKey(const Key('report-narrative-0')));
      expect(narrative.data, hostile, reason: 'the text is shown exactly as it came, as text');
      expect(find.descendant(of: find.byKey(const Key('report-narrative')), matching: find.byType(SelectionArea)), findsOneWidget);
      expect(find.byType(Image), findsNothing);
      // and it is apart from the records, which keep their own label
      expect(find.byKey(const Key('report-narrative-warning')), findsOneWidget);
    });
  });

  group('team report', () {
    testWidgets('a supervisor asks the team report and sees team figures and each person apart, with no ranking', (tester) async {
      final s = Setup();
      await openTeam(tester, s, submit: false);
      expect(find.byKey(const Key('team-report-none')), findsOneWidget);
      await tapKey(tester, 'team-report-submit');
      expect(s.reports.teamRequests, [
        {'from': DateTime.utc(2026, 10, 31), 'to': DateTime.utc(2026, 11, 6)},
      ]);
      expect(find.byKey(const Key('team-report-result')), findsOneWidget);
      expect(find.byKey(const Key('team-report-base')), findsOneWidget);
      expect(find.text('Informe del equipo'), findsWidgets);
      // team figures first (deterministic, no narrative of their own)
      expect(find.byKey(const Key('team-metrics')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('team-metric-avances')), matching: find.text('8')), findsOneWidget);
      // then each person with at least one entry, in the order the server gives
      expect(find.text('Personas con registros en el período (2)'), findsOneWidget);
      expect(find.byKey(const Key('team-report-person-0-name')), findsOneWidget);
      expect(textOf(tester, 'team-report-person-0-name'), 'Ana Compañera');
      expect(textOf(tester, 'team-report-person-1-name'), 'Sara Supervisora');
      expect(find.text('Ana trabajó en el informe mensual.'), findsOneWidget);
      expect(find.text('Sara registró avances.'), findsOneWidget);
      expect(find.byKey(const Key('team-person-0-metrics')), findsOneWidget);
      expect(find.byKey(const Key('team-person-1-facts')), findsOneWidget);
      expect(find.text('REDACTADO CON IA'), findsNWidgets(2), reason: 'one narrative per person and none for the team section');
      expect(find.textContaining('no es una clasificación'), findsOneWidget);
      expectReadOnly();
      // the team section is not a ranking: the words of a ranking appear nowhere (the explanatory note names none)
      for (final word in ['ranking', 'Ranking', 'puntuación', 'Puntuación', 'rendimiento', 'Rendimiento', '%']) {
        expect(find.textContaining(word), findsNothing, reason: word);
      }
    });

    testWidgets('a team without entries shows no people, the base and no report made up for anyone', (tester) async {
      final s = Setup()..reports.teamAnswer = sampleTeam(noData: true);
      await openTeam(tester, s);
      expect(find.byKey(const Key('team-report-no-data')), findsOneWidget);
      expect(find.byKey(const Key('team-report-base')), findsOneWidget);
      expect(find.byKey(const Key('team-metrics')), findsNothing);
      expect(find.byKey(const Key('team-report-people-title')), findsNothing);
      expect(find.byKey(const Key('team-report-person-0')), findsNothing);
    });

    testWidgets('a neutral activity of a person is shown with the fixed label only', (tester) async {
      await openTeam(tester, Setup());
      final neutralFact = find.descendant(of: find.byKey(const Key('team-report-person-0')), matching: find.byKey(const Key('team-person-0-fact-2')));
      expect(find.descendant(of: neutralFact, matching: find.text('Actividad en continuidad')), findsOneWidget);
      expect(find.descendant(of: neutralFact, matching: find.text('Preparar informe mensual')), findsNothing);
    });

    testWidgets('a collaborator-like rejection: the server says no and nothing is shown; the same for a limit', (tester) async {
      final s = Setup();
      await openTeam(tester, s);
      expect(find.byKey(const Key('team-report-result')), findsOneWidget);
      s.reports.teamAnswer = reportError('OPERACION_NO_PERMITIDA', status: 403);
      await tapKey(tester, 'team-report-submit');
      expect(find.byKey(const Key('team-report-result')), findsNothing);
      expect(find.text('Ana trabajó en el informe mensual.'), findsNothing);
      expect(textOf(tester, 'report-error-text'), 'Esta operación no está permitida para tu rol.');
      s.reports.teamAnswer = reportError('INFORME_EXCEDE_LIMITES', status: 422, details: [
        {'campo': 'hechos', 'motivo': 'hechos_exceden_el_maximo', 'maximo_hechos': 400},
        {'campo': 'reintento', 'reintento': false, 'motivo': 'no_aplicable'},
      ]);
      await tapKey(tester, 'team-report-submit');
      expect(textOf(tester, 'report-error-text'), contains('más de 400 registros'));
      expect(find.byKey(const Key('report-retry')), findsNothing);
    });

    testWidgets('while it generates the team report asks only once and a technical failure can be retried by hand', (tester) async {
      final s = Setup()..reports.gate = Completer<void>();
      await openTeam(tester, s, submit: false);
      await tester.tap(find.byKey(const Key('team-report-submit')));
      await tester.pump();
      expect(find.byKey(const Key('report-generating')), findsOneWidget);
      await tester.tap(find.byKey(const Key('team-report-submit')), warnIfMissed: false);
      await tester.pump();
      expect(s.reports.teamRequests, hasLength(1));
      s.reports
        ..teamAnswer = notGenerated(retry: true)
        ..gate!.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('report-retry')), findsOneWidget);
      s.reports
        ..gate = null
        ..teamAnswer = sampleTeam();
      await tapKey(tester, 'report-retry');
      expect(s.reports.teamRequests, hasLength(2));
      expect(find.byKey(const Key('team-report-result')), findsOneWidget);
    });
  });

  group('responsive', () {
    testWidgets('on a phone the individual report is reached from the menu and shows without overflow', (tester) async {
      final s = Setup();
      await openIndividual(tester, s, size: mobile);
      expect(find.byKey(const Key('report-result')), findsOneWidget);
      expect(find.text('Preparar informe mensual'), findsWidgets);
      expect(tester.takeException(), isNull);
    });

    testWidgets('on a phone the team report shows every person without overflow', (tester) async {
      await openTeam(tester, Setup(), size: mobile);
      expect(find.byKey(const Key('team-report-result')), findsOneWidget);
      await tester.ensureVisible(find.byKey(const Key('team-report-person-1')));
      expect(tester.takeException(), isNull);
    });
  });

  group('session and memory', () {
    test('the answer of a request made by a session that ended is discarded, never shown to the next one', () async {
      final repo = FakeReportRepository()
        ..individualAnswer = sampleIndividual()
        ..gate = Completer<void>();
      final container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
          reportRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);
      await container.read(authProvider.future);
      container.listen(individualReportControllerProvider, (_, _) {});
      final pending = container.read(individualReportControllerProvider.notifier).generate(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect(container.read(individualReportControllerProvider).isGenerating, true);
      container.read(authProvider.notifier).expired();
      repo.gate!.complete();
      await pending;
      expect(container.read(individualReportControllerProvider).phase, ReportPhase.idle);
      expect(container.read(individualReportControllerProvider).report, isNull);
    });

    test('a server that no longer recognizes the session sends the app back to the login and keeps no report', () async {
      final repo = FakeReportRepository()..individualAnswer = reportError('NO_IDENTIFICADA', status: 401);
      final container = ProviderContainer(
        overrides: [
          authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession())),
          reportRepositoryProvider.overrideWithValue(repo),
        ],
      );
      addTearDown(container.dispose);
      await container.read(authProvider.future);
      container.listen(individualReportControllerProvider, (_, _) {});
      await container.read(individualReportControllerProvider.notifier).generate(from: DateTime.utc(2026, 10, 31), to: DateTime.utc(2026, 11, 6));
      expect(container.read(authProvider).value, isNull);
      expect(container.read(individualReportControllerProvider).report, isNull);
    });
  });
}
