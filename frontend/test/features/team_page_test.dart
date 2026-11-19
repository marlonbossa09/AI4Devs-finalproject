import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/team/domain/entities/team_entities.dart';
import 'package:smartwork/features/team/presentation/providers/team_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';
import '../helpers/team_fakes.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

Future<void> pumpApp(
  WidgetTester tester, {
  required FakeTeamRepository team,
  Role role = Role.collaborator,
  Size size = desktop,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
        logbookRepositoryProvider.overrideWithValue(FakeLogbookRepository()),
        teamRepositoryProvider.overrideWithValue(team),
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

Future<void> openTeam(WidgetTester tester, FakeTeamRepository team, {Role role = Role.collaborator, Size size = desktop}) async {
  await pumpApp(tester, team: team, role: role, size: size);
  await tapKey(tester, 'nav-team');
}

/// Chooses a person in the list of people (a row of the group found by [selectKey]).
Future<void> choose(WidgetTester tester, String selectKey, String label) async {
  final row = find.descendant(of: find.byKey(Key(selectKey)), matching: find.text(label));
  await tester.ensureVisible(row);
  await tester.pumpAndSettle();
  await tester.tap(row);
  await tester.pumpAndSettle();
}

/// Words of any action that changes a record: none of them may appear in a read-only view of someone else's records.
const editWords = ['Registrar avance', 'Guardar', 'Cerrar jornada', 'Reabrir', 'Corregir', 'Reactivar', 'Marcar como', 'Planificar continuación', 'Editar'];

void expectReadOnly() {
  for (final word in editWords) {
    expect(find.textContaining(word), findsNothing, reason: word);
  }
  expect(find.byType(TextField), findsNothing);
  expect(find.byType(TextFormField), findsNothing);
}

void main() {
  setUpAll(loadTestFonts);

  group('how it is reached', () {
    testWidgets('Mi equipo is offered to a collaborator and to a supervisor, and asks the members once', (tester) async {
      for (final role in [Role.collaborator, Role.supervisor]) {
        final team = FakeTeamRepository();
        await pumpApp(tester, team: team, role: role);
        expect(find.byKey(const Key('nav-team')), findsOneWidget, reason: '$role');
        await tapKey(tester, 'nav-team');
        expect(find.text('Mi equipo'), findsWidgets);
        expect(team.memberRequests, 1);
      }
    });
  });

  group('colleague picker (M4-05)', () {
    testWidgets('lists the CURRENT colleagues, not the user, and tells the supervisor apart by a word', (tester) async {
      await openTeam(tester, FakeTeamRepository());
      final list = find.byKey(const Key('peer-select'));
      expect(find.descendant(of: list, matching: find.text('Ana Compañera')), findsOneWidget);
      expect(find.descendant(of: list, matching: find.text('Sara Supervisora')), findsOneWidget);
      expect(find.descendant(of: list, matching: find.text('Supervisor')), findsOneWidget);
      expect(find.descendant(of: list, matching: find.text('Colaborador')), findsOneWidget);
      expect(find.descendant(of: list, matching: find.text('Carlos Colaborador')), findsNothing);
    });

    testWidgets('a team of one has no colleagues to choose: it says so', (tester) async {
      await openTeam(tester, FakeTeamRepository(members: [FakeTeamRepository.defaultMembers.first]));
      expect(find.byKey(const Key('team-no-colleagues')), findsOneWidget);
      expect(find.byKey(const Key('peer-select')), findsNothing);
    });

    testWidgets('a failure to load the team is an error with retry, and an access error uses its own fixed text', (tester) async {
      final team = FakeTeamRepository()..membersError = const ApiError(code: ApiError.network, message: 'Sin conexión');
      await openTeam(tester, team);
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
      team.membersError = null;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('peer-select')), findsOneWidget);

      final desactivado = FakeTeamRepository()..membersError = const ApiError(code: 'ACCESO_DESACTIVADO', message: 'PAYLOAD DEL SERVIDOR');
      await openTeam(tester, desactivado);
      expect(find.textContaining('Tu acceso está desactivado'), findsOneWidget);
      expect(find.textContaining('PAYLOAD'), findsNothing);
    });
  });

  group('a colleague logbook (M4-01)', () {
    testWidgets('is read-only: title, neutral reference, block reason and summary, with no way to change anything', (tester) async {
      final team = FakeTeamRepository()
        ..logbooks['p2|2026-11-06'] = peerLogbook(
          activities: [
            fullActivity('a1', 'Preparar informe', status: ActivityStatus.blocked),
            neutralActivity('a2'),
          ],
          progress: [
            PeerProgress(activityId: 'a1', date: today, status: ActivityStatus.blocked, description: 'Esperando datos', blockReason: 'Falta el acceso'),
          ],
          plannings: [PeerPlanning(activityId: 'a1', date: today, type: PlanningType.original, description: 'Revisar cifras')],
        );
      await openTeam(tester, team);
      await choose(tester, 'peer-select', 'Ana Compañera'); // choosing asks for the logbook at once
      expect(team.logbookRequests.single['personId'], 'p2');
      expect(team.logbookRequests.single['date'], today);
      expect(find.byKey(const Key('peer-logbook')), findsOneWidget);
      expect(find.text('Resumen de Ana'), findsOneWidget);
      expect(find.text('Preparar informe'), findsOneWidget);
      expect(find.text('Esperando datos'), findsOneWidget);
      expect(find.textContaining('Falta el acceso'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      expect(find.byKey(const Key('peer-readonly-note')), findsOneWidget);
      expectReadOnly();
    });

    testWidgets('a neutral activity shows ONLY "Actividad en continuidad": nothing else of it', (tester) async {
      final team = FakeTeamRepository()
        ..logbooks['p2|2026-11-06'] = peerLogbook(
          activities: [neutralActivity('a2')],
          progress: [PeerProgress(activityId: 'a2', date: today, status: ActivityStatus.inProgress, description: 'Seguí con ello')],
        );
      await openTeam(tester, team);
      await choose(tester, 'peer-select', 'Ana Compañera');
      await tapKey(tester, 'peer-submit');
      expect(find.byKey(const Key('neutral-label')), findsOneWidget);
      expect(find.text('Actividad en continuidad'), findsOneWidget);
      expect(find.text('Seguí con ello'), findsOneWidget, reason: 'the colleague own progress detail of this logbook is shown');
      expect(find.descendant(of: find.byKey(const Key('shared-activity-a2')), matching: find.byType(InkWell)), findsNothing, reason: 'a neutral reference opens nothing');
      expect(find.descendant(of: find.byKey(const Key('shared-activity-a2')), matching: find.byType(GestureDetector)), findsNothing);
      expectReadOnly();
    });

    testWidgets('no logbook (or none the user may read) is one neutral message, not a guess', (tester) async {
      await openTeam(tester, FakeTeamRepository());
      await choose(tester, 'peer-select', 'Ana Compañera');
      await tapKey(tester, 'peer-submit');
      expect(find.byKey(const Key('peer-unavailable')), findsOneWidget);
      expect(find.textContaining('No hay una bitácora disponible'), findsOneWidget);
    });

    testWidgets('a connection error is shown as such and can be retried', (tester) async {
      final team = FakeTeamRepository()..logbookError = const ApiError(code: ApiError.network, message: 'Sin conexión');
      await openTeam(tester, team);
      await choose(tester, 'peer-select', 'Ana Compañera');
      await tapKey(tester, 'peer-submit');
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
      team.logbookError = null;
      team.logbooks['p2|2026-11-06'] = peerLogbook();
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('peer-logbook')), findsOneWidget);
    });
  });

  group('history (M4-02)', () {
    FakeTeamRepository withHistory() => FakeTeamRepository()
      ..history = [
        historyEntry('p2', DateTime.utc(2026, 11, 3), summary: 'Lunes de Ana', activities: [fullActivity('a1', 'Informe')]),
        historyEntry('p3', DateTime.utc(2026, 11, 4), summary: 'Martes de Sara', activities: [neutralActivity('a2', owner: 'p3')]),
        historyEntry('p9', DateTime.utc(2026, 11, 5), summary: 'De alguien que salió'),
        historyEntry('p1', DateTime.utc(2026, 11, 6), summary: 'Mío'),
      ];

    Future<void> openHistory(WidgetTester tester, FakeTeamRepository team, {Size size = desktop}) async {
      await openTeam(tester, team, size: size);
      await tapKey(tester, 'team-mode');
      await tester.tap(find.text('Histórico'));
      await tester.pumpAndSettle();
    }

    testWidgets('sends the range (always) and shows the first page, with a "Ver más" that follows the server cursor', (tester) async {
      final team = withHistory();
      await openHistory(tester, team);
      expect(find.byKey(const Key('history-none')), findsOneWidget, reason: 'nothing is asked until the user does');
      await tapKey(tester, 'history-submit');
      final first = team.historyRequests.single;
      expect(first['from'], addDays(today, -6));
      expect(first['to'], today);
      expect(first['personId'], isNull);
      expect(first['cursor'], isNull);
      expect(find.text('Lunes de Ana'), findsOneWidget);
      expect(find.text('Martes de Sara'), findsOneWidget);
      expect(find.text('De alguien que salió'), findsNothing);
      await tapKey(tester, 'history-load-more');
      expect(team.historyRequests.last['cursor'], '2');
      expect(find.text('De alguien que salió'), findsOneWidget);
      expect(find.text('Mío'), findsOneWidget);
      expect(find.byKey(const Key('history-load-more')), findsNothing, reason: 'no more pages');
      expect(find.text('Lunes de Ana'), findsOneWidget, reason: 'nothing repeated');
      expectReadOnly();
    });

    testWidgets('names people from the current team and does not invent a name for someone who left', (tester) async {
      final team = withHistory()..pageSize = 10;
      await openHistory(tester, team);
      await tapKey(tester, 'history-submit');
      expect(find.descendant(of: find.byKey(const Key('history-entry-p2-2026-11-03')), matching: find.text('Ana Compañera')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('history-entry-p1-2026-11-06')), matching: find.text('Tú')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('history-entry-p9-2026-11-05')), matching: find.text('Persona que ya no está en tu equipo')), findsOneWidget);
    });

    testWidgets('the optional person filter is sent only when chosen', (tester) async {
      final team = withHistory()..pageSize = 10;
      await openHistory(tester, team);
      await choose(tester, 'history-person', 'Ana Compañera');
      await tapKey(tester, 'history-submit');
      expect(team.historyRequests.single['personId'], 'p2');
      expect(find.text('Lunes de Ana'), findsOneWidget);
      expect(find.text('Martes de Sara'), findsNothing);
    });

    testWidgets('neutral activities in the history are neutral too', (tester) async {
      final team = withHistory()..pageSize = 10;
      await openHistory(tester, team);
      await tapKey(tester, 'history-submit');
      expect(find.text('Actividad en continuidad'), findsOneWidget);
      expect(find.text('Informe'), findsOneWidget);
    });

    testWidgets('an empty result and a failure to load more are distinct from each other and from a connection error', (tester) async {
      final empty = FakeTeamRepository();
      await openHistory(tester, empty);
      await tapKey(tester, 'history-submit');
      expect(find.byKey(const Key('history-empty')), findsOneWidget);

      final more = withHistory()..moreErrors.add(const ApiError(code: ApiError.network, message: 'Sin conexión'));
      await openHistory(tester, more);
      await tapKey(tester, 'history-submit');
      await tapKey(tester, 'history-load-more');
      expect(find.byKey(const Key('history-more-error')), findsOneWidget);
      expect(find.text('Lunes de Ana'), findsOneWidget, reason: 'the pages already loaded stay');
      await tapKey(tester, 'history-load-more');
      expect(find.text('Mío'), findsOneWidget);

      final down = FakeTeamRepository()..historyError = const ApiError(code: ApiError.network, message: 'Sin conexión');
      await openHistory(tester, down);
      await tapKey(tester, 'history-submit');
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);

      final forbidden = FakeTeamRepository()..historyError = const ApiError(code: 'SIN_PERTENENCIA_VIGENTE', message: 'x');
      await openHistory(tester, forbidden);
      await tapKey(tester, 'history-submit');
      expect(find.textContaining('No tienes una pertenencia vigente'), findsOneWidget);
    });

    testWidgets('a range that cannot be sent is not sent: end before start, and more than 92 days', (tester) async {
      final team = withHistory();
      await openHistory(tester, team);
      // End before start: move "Hasta" back one month and pick the 30th (before the default start, Oct 31)
      await tapKey(tester, 'history-to');
      await tester.tap(find.byTooltip('Previous month'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('30').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'history-submit');
      expect(find.text('La fecha inicial no puede ser posterior a la final.'), findsOneWidget);
      expect(team.historyRequests, isEmpty);

      // Back to a valid end, and a start more than 92 days earlier
      await tapKey(tester, 'history-to');
      await tester.tap(find.text('6').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'history-from');
      for (var i = 0; i < 4; i++) {
        await tester.tap(find.byTooltip('Previous month'));
        await tester.pumpAndSettle();
      }
      await tester.tap(find.text('1').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'history-submit');
      expect(find.text('El rango puede abarcar como máximo 92 días.'), findsOneWidget);
      expect(team.historyRequests, isEmpty, reason: 'nothing was sent');
    });
  });

  group('losing the authorization while looking at data', () {
    testWidgets('asking again for a logbook or the history after a rejection shows the rejection and NO earlier data', (tester) async {
      final team = FakeTeamRepository()
        ..logbooks['p2|2026-11-06'] = peerLogbook(summary: 'Resumen que no debe quedar a la vista')
        ..history = [historyEntry('p2', DateTime.utc(2026, 11, 3), summary: 'Histórico que no debe quedar a la vista')]
        ..pageSize = 10;
      await openTeam(tester, team);
      await choose(tester, 'peer-select', 'Ana Compañera');
      expect(find.text('Resumen que no debe quedar a la vista'), findsOneWidget);
      team.logbookError = const ApiError(code: 'ACCESO_DESACTIVADO', message: 'PAYLOAD');
      await tapKey(tester, 'peer-submit');
      expect(team.logbookRequests.length, 2);
      expect(find.textContaining('Tu acceso está desactivado'), findsOneWidget);
      expect(find.text('Resumen que no debe quedar a la vista'), findsNothing);

      await tapKey(tester, 'team-mode');
      await tester.tap(find.text('Histórico'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'history-submit');
      expect(find.text('Histórico que no debe quedar a la vista'), findsOneWidget);
      team.historyError = const ApiError(code: 'SIN_PERTENENCIA_VIGENTE', message: 'PAYLOAD');
      await tapKey(tester, 'history-submit');
      expect(team.historyRequests.length, 2);
      expect(find.textContaining('No tienes una pertenencia vigente'), findsOneWidget);
      expect(find.text('Histórico que no debe quedar a la vista'), findsNothing);
    });
  });

  group('layout', () {
    for (final (name, size) in [('mobile', mobile), ('tablet', tablet), ('desktop', desktop)]) {
      testWidgets('both views fit on $name without overflow', (tester) async {
        final team = FakeTeamRepository()
          ..logbooks['p2|2026-11-06'] = peerLogbook(
            summary: 'Un resumen bastante largo para comprobar que el texto se ajusta al ancho disponible sin desbordar la pantalla en ningún tamaño.',
            activities: [fullActivity('a1', 'Una actividad con un título largo que ocupa varias líneas en una pantalla estrecha', status: ActivityStatus.inProgress, markReason: 'Duplicada'), neutralActivity('a2')],
          )
          ..history = [historyEntry('p2', DateTime.utc(2026, 11, 3), summary: 'Lunes', activities: [neutralActivity('a2')])];
        await openTeam(tester, team, size: size);
        await choose(tester, 'peer-select', 'Ana Compañera');
        await tapKey(tester, 'peer-submit');
        expect(find.byKey(const Key('peer-logbook')), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'team-mode');
        await tester.tap(find.text('Histórico'));
        await tester.pumpAndSettle();
        await tapKey(tester, 'history-submit');
        expect(find.byKey(const Key('history-list')), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
