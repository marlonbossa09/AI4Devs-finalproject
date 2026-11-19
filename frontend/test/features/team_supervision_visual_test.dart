import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/supervision/domain/entities/supervision_entities.dart';
import 'package:smartwork/features/supervision/presentation/providers/supervision_repository.dart';
import 'package:smartwork/features/team/domain/entities/team_entities.dart';
import 'package:smartwork/features/team/presentation/providers/team_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';
import '../helpers/supervision_fakes.dart';
import '../helpers/team_fakes.dart';

/// Visual redesign of "Mi equipo" and "Supervisión" (UX-T7). They are two independent screens: the first lists the people of
/// the team and reads what is chosen; the second reads a period of the whole team. These tests check how they are laid out,
/// that nothing is asked of the server before the user asks, that the states are told in words, that nothing overflows, and
/// that neither screen shows a ranking, a percentage or a clock time. What each one asks and says stays in
/// `team_page_test.dart` and `supervision_page_test.dart`.

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

class Rig {
  Rig({FakeTeamRepository? team, FakeSupervisionRepository? supervision})
    : team = team ?? FakeTeamRepository(),
      supervision = supervision ?? FakeSupervisionRepository(),
      logbook = FakeLogbookRepository();

  final FakeTeamRepository team;
  final FakeSupervisionRepository supervision;
  final FakeLogbookRepository logbook;
}

Future<void> pumpApp(WidgetTester tester, Rig rig, {Size size = desktop, double textScale = 1, Role role = Role.supervisor}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
        logbookRepositoryProvider.overrideWithValue(rig.logbook),
        teamRepositoryProvider.overrideWithValue(rig.team),
        supervisionRepositoryProvider.overrideWithValue(rig.supervision),
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

Future<void> choose(WidgetTester tester, String listKey, String label) async {
  final row = find.descendant(of: find.byKey(Key(listKey)), matching: find.text(label));
  await tester.ensureVisible(row);
  await tester.pumpAndSettle();
  await tester.tap(row);
  await tester.pumpAndSettle();
}

Future<void> openTeam(WidgetTester tester, Rig rig, {Size size = desktop, double textScale = 1, Role role = Role.supervisor}) async {
  await pumpApp(tester, rig, size: size, textScale: textScale, role: role);
  await tapKey(tester, 'nav-team');
}

Future<void> openSupervision(WidgetTester tester, Rig rig, {Size size = desktop, double textScale = 1, bool submit = true}) async {
  await pumpApp(tester, rig, size: size, textScale: textScale);
  await tapKey(tester, 'nav-supervision');
  if (submit) await tapKey(tester, 'supervision-submit');
}

Future<void> showHistory(WidgetTester tester) async {
  await tapKey(tester, 'team-mode');
  await tester.tap(find.text('Histórico'));
  await tester.pumpAndSettle();
}

/// Every piece of text on screen.
List<String> allTexts(WidgetTester tester) => [
  for (final text in tester.widgetList<Text>(find.byType(Text))) text.data ?? text.textSpan?.toPlainText() ?? '',
];

const rankingWords = ['ranking', 'Ranking', 'puntuación', 'Puntuación', 'mejor', 'peor', 'rendimiento', 'Rendimiento', 'promedio', 'Promedio'];

/// No ranking, no score, no percentage and no clock time anywhere on screen.
void expectNoRankingPercentOrClock(WidgetTester tester) {
  final clock = RegExp(r'\b\d{1,2}:\d{2}\b');
  for (final text in allTexts(tester)) {
    expect(text.contains('%'), isFalse, reason: 'percentage in "$text"');
    expect(clock.hasMatch(text), isFalse, reason: 'clock time in "$text"');
    for (final word in rankingWords) {
      expect(text.contains(word), isFalse, reason: '"$word" in "$text"');
    }
  }
}

Rig richRig() {
  const longSummary =
      'Un resumen bastante largo para comprobar que el texto se ajusta al ancho disponible sin desbordar la pantalla en ningún tamaño ni con el texto ampliado.';
  const longTitle = 'Una actividad con un título largo que ocupa varias líneas en una pantalla estrecha';
  final team = FakeTeamRepository()
    ..pageSize = 10
    ..logbooks['p2|2026-11-06'] = peerLogbook(
      summary: longSummary,
      activities: [
        fullActivity('a1', longTitle, status: ActivityStatus.blocked, markReason: 'Duplicada'),
        neutralActivity('a2'),
      ],
      progress: [
        PeerProgress(activityId: 'a1', date: today, status: ActivityStatus.blocked, description: 'Esperando datos del cliente para seguir', blockReason: 'Falta el acceso'),
      ],
      plannings: [PeerPlanning(activityId: 'a1', date: today, type: PlanningType.original, description: 'Revisar cifras del trimestre')],
    )
    ..history = [
      historyEntry('p2', DateTime.utc(2026, 11, 3), summary: longSummary, activities: [fullActivity('a1', longTitle), neutralActivity('a2')]),
      historyEntry('p9', DateTime.utc(2026, 11, 4), summary: 'De alguien que salió'),
    ];
  final supervision = FakeSupervisionRepository()
    ..pageSize = 10
    ..items = [
      supervised(
        'a1',
        longTitle,
        reasons: [InclusionReason.plannedInPeriod, InclusionReason.withProgressInPeriod, InclusionReason.pendingAtCut],
        atCut: ActivityStatus.blocked,
        currentIfDiffers: ActivityStatus.completed,
      ),
      supervised('a5', 'Sin estado al corte visible', atCut: null),
      supervisedNeutral('a2', atCut: ActivityStatus.inProgress),
      minimalReference('a3', owner: 'p3', last: DateTime.utc(2026, 11, 4)),
    ];
  supervision.histories['a1'] = ActivityHistoryDetail(
    activity: fullActivity('a1', longTitle, markReason: 'Duplicada'),
    plannings: [PeerPlanning(activityId: 'a1', date: DateTime.utc(2026, 11, 1), type: PlanningType.original, description: 'Revisar cifras del trimestre')],
    progress: [
      PeerProgress(activityId: 'a1', date: DateTime.utc(2026, 11, 2), status: ActivityStatus.inProgress, description: 'Primer avance'),
      PeerProgress(activityId: 'a1', date: DateTime.utc(2026, 11, 5), status: ActivityStatus.blocked, description: 'Segundo avance', blockReason: 'Falta el acceso al sistema del cliente'),
    ],
    currentStatus: ActivityStatus.completed,
  );
  supervision.histories['a2'] = ActivityHistoryDetail(
    activity: neutralActivity('a2'),
    plannings: const [],
    progress: [PeerProgress(activityId: 'a2', date: DateTime.utc(2026, 11, 5), status: ActivityStatus.inProgress, description: 'Avance propio de este equipo')],
  );
  supervision.histories['a3'] = ActivityHistoryReference(minimalReference('a3', owner: 'p3', last: DateTime.utc(2026, 11, 4)));
  return Rig(team: team, supervision: supervision);
}

void main() {
  setUpAll(loadTestFonts);

  group('two independent screens', () {
    testWidgets('each has its own entry and its own page: neither shows nor asks anything of the other', (tester) async {
      final rig = richRig();
      await pumpApp(tester, rig);
      expect(find.byKey(const Key('nav-team')), findsOneWidget);
      expect(find.byKey(const Key('nav-supervision')), findsOneWidget);

      await tapKey(tester, 'nav-team');
      expect(find.byKey(const Key('team-master')), findsOneWidget);
      expect(find.byKey(const Key('team-mode')), findsOneWidget);
      expect(find.byKey(const Key('supervision-submit')), findsNothing);
      expect(find.byKey(const Key('supervision-hint')), findsNothing);
      expect(rig.supervision.supervisionRequests, isEmpty, reason: 'Mi equipo asks nothing of the supervision');

      await tapKey(tester, 'nav-supervision');
      expect(find.byKey(const Key('supervision-submit')), findsOneWidget);
      expect(find.byKey(const Key('team-master')), findsNothing);
      expect(find.byKey(const Key('team-mode')), findsNothing);
      expect(find.byKey(const Key('peer-submit')), findsNothing);
      expect(rig.team.logbookRequests, isEmpty, reason: 'the supervision asks no logbook of a colleague');
      expect(rig.team.historyRequests, isEmpty, reason: 'the supervision asks no history of the team');
    });
  });

  group('Mi equipo: list and detail', () {
    for (final (name, size) in [('desktop', desktop), ('tablet', tablet), ('mobile', mobile)]) {
      testWidgets('on $name the list is ${size == desktop ? 'beside' : 'above'} the detail', (tester) async {
        await openTeam(tester, richRig(), size: size);
        final master = tester.getRect(find.byKey(const Key('team-master')));
        final detail = tester.getRect(find.byKey(const Key('team-detail')));
        if (size == desktop) {
          expect(master.width, 320);
          expect(detail.left, greaterThanOrEqualTo(master.right));
          expect((detail.top - master.top).abs(), lessThan(1), reason: 'both start on the same line');
          expect(detail.width, greaterThan(master.width));
        } else {
          expect(detail.top, greaterThanOrEqualTo(master.bottom), reason: 'the detail goes under the list');
          expect(detail.left, master.left);
          expect(detail.width, master.width);
        }
        // The people are visible at once and each row is compact
        for (final id in ['p2', 'p3']) {
          final row = tester.getRect(find.byKey(Key('team-member-$id')));
          expect(row.height, lessThanOrEqualTo(60), reason: id);
          expect(row.height, greaterThanOrEqualTo(40), reason: 'a touch target');
          expect(master.contains(row.center), isTrue, reason: '$id is inside the list');
        }
        expect(find.byKey(const Key('team-member-p1')), findsNothing, reason: 'the user is not offered as a colleague');
      });
    }

    testWidgets('the chosen person is told by the detail header, by a check and by the selected state, not only by color', (tester) async {
      final handle = tester.ensureSemantics();
      await openTeam(tester, richRig());
      bool selected(String id) => tester.getSemantics(find.byKey(Key('team-member-$id'))).flagsCollection.isSelected;
      expect(selected('p2'), isFalse);
      expect(find.byIcon(Icons.check_circle), findsNothing);
      await choose(tester, 'peer-select', 'Ana Compañera');
      expect(selected('p2'), isTrue);
      expect(selected('p3'), isFalse);
      expect(find.descendant(of: find.byKey(const Key('team-member-p2')), matching: find.byIcon(Icons.check_circle)), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('team-detail')), matching: find.text('Ana Compañera')), findsOneWidget, reason: 'the detail names who it is about');
      expect(find.text('Colaborador · bitácora en solo lectura'), findsOneWidget);
      handle.dispose();
    });

    testWidgets('the history has its own list of people, with the "everybody" row and the user told by a word', (tester) async {
      await openTeam(tester, richRig());
      await showHistory(tester);
      final list = find.byKey(const Key('history-person'));
      expect(find.descendant(of: list, matching: find.text('Todas las personas que puedo consultar')), findsOneWidget);
      expect(find.descendant(of: list, matching: find.text('Carlos Colaborador')), findsOneWidget);
      expect(find.descendant(of: list, matching: find.text('Tú · Colaborador')), findsOneWidget);
      expect(find.text('Persona: todas las que puedes consultar'), findsOneWidget);
      await choose(tester, 'history-person', 'Ana Compañera');
      expect(find.text('Persona: Ana Compañera'), findsOneWidget);
    });
  });

  group('Mi equipo: nothing is loaded before the user asks', () {
    testWidgets('the members are asked once; a logbook is asked when a person is chosen, and never before', (tester) async {
      final rig = richRig();
      await openTeam(tester, rig);
      expect(rig.team.memberRequests, 1);
      expect(rig.team.logbookRequests, isEmpty);
      expect(rig.team.historyRequests, isEmpty);
      FilledButton submit() => tester.widget<FilledButton>(find.descendant(of: find.byKey(const Key('peer-submit')), matching: find.byType(FilledButton)));
      expect(submit().onPressed, isNull, reason: 'without a person there is nothing to ask');
      expect(find.byKey(const Key('peer-none')), findsOneWidget);

      await choose(tester, 'peer-select', 'Ana Compañera');
      expect(rig.team.logbookRequests.length, 1, reason: 'choosing a person asks for their logbook');
      expect(rig.team.logbookRequests.single['personId'], 'p2');
      expect(find.byKey(const Key('peer-logbook')), findsOneWidget);
      expect(submit().onPressed, isNotNull);

      // Choosing someone else asks for THEIR logbook; the previous answer does not stay on screen
      await choose(tester, 'peer-select', 'Sara Supervisora');
      expect(rig.team.logbookRequests.length, 2);
      expect(rig.team.logbookRequests.last['personId'], 'p3');
      expect(rig.team.memberRequests, 1, reason: 'the members are not asked again');
      // The button asks again on purpose (the answer is never reused from memory)
      await tapKey(tester, 'peer-submit');
      expect(rig.team.logbookRequests.length, 3);
    });

    testWidgets('the history is asked only on "Consultar histórico", not when the mode or the person changes', (tester) async {
      final rig = richRig();
      await openTeam(tester, rig);
      await showHistory(tester);
      expect(rig.team.historyRequests, isEmpty);
      expect(find.byKey(const Key('history-none')), findsOneWidget);
      await choose(tester, 'history-person', 'Ana Compañera');
      expect(rig.team.historyRequests, isEmpty);
      await tapKey(tester, 'history-submit');
      expect(rig.team.historyRequests.length, 1);
      expect(rig.team.historyRequests.single['personId'], 'p2');
      expect(rig.team.logbookRequests, isEmpty, reason: 'the history asks no colleague logbook');
    });
  });

  group('Mi equipo: states', () {
    testWidgets('a team of one: the logbook says there is nobody to read, with no list and no form', (tester) async {
      await openTeam(tester, Rig(team: FakeTeamRepository(members: [FakeTeamRepository.defaultMembers.first])));
      expect(find.byKey(const Key('team-no-colleagues')), findsOneWidget);
      expect(find.byKey(const Key('team-master')), findsNothing);
      expect(find.byKey(const Key('peer-submit')), findsNothing);
    });

    testWidgets('a team that cannot be loaded is one error with retry, and then the list appears', (tester) async {
      final team = FakeTeamRepository()..membersError = const ApiError(code: ApiError.network, message: 'Sin conexión');
      await openTeam(tester, Rig(team: team));
      expect(find.byKey(const Key('load-error')), findsOneWidget);
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
      expect(find.byKey(const Key('team-master')), findsNothing);
      team.membersError = null;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('team-master')), findsOneWidget);
    });

    testWidgets('no logbook, an empty history and a failed history are three different messages', (tester) async {
      final rig = Rig(team: FakeTeamRepository());
      await openTeam(tester, rig);
      await choose(tester, 'peer-select', 'Ana Compañera');
      await tapKey(tester, 'peer-submit');
      expect(find.byKey(const Key('peer-unavailable')), findsOneWidget);
      await showHistory(tester);
      await tapKey(tester, 'history-submit');
      expect(find.byKey(const Key('history-empty')), findsOneWidget);
      rig.team.historyError = const ApiError(code: ApiError.network, message: 'Sin conexión');
      await tapKey(tester, 'history-submit');
      expect(find.byKey(const Key('history-empty')), findsNothing);
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
    });

    testWidgets('what is read is told read-only, and a closed or open logbook is told in words', (tester) async {
      await openTeam(tester, richRig());
      await choose(tester, 'peer-select', 'Ana Compañera');
      await tapKey(tester, 'peer-submit');
      expect(find.byKey(const Key('peer-readonly-note')), findsOneWidget);
      expect(find.text('Abierta'), findsOneWidget);
      expect(find.text('Bloqueada'), findsWidgets, reason: 'a status always carries its word');
    });
  });

  group('Supervisión: summary, rows and status at the cut', () {
    testWidgets('the period, the cut and the totals come first; the activities are dense rows under them', (tester) async {
      await openSupervision(tester, richRig());
      final period = tester.getTopLeft(find.byKey(const Key('supervision-period')));
      final totals = tester.getTopLeft(find.byKey(const Key('supervision-totals')));
      final first = tester.getTopLeft(find.byKey(const Key('supervision-item-a1')));
      expect(period.dy, lessThan(totals.dy));
      expect(totals.dy, lessThan(first.dy));
      expect(find.byKey(const Key('totals-scope')), findsOneWidget);
      expect(find.text('Actividades por estado al corte'), findsOneWidget);
      for (final key in ['total-pending', 'total-inProgress', 'total-blocked', 'total-completed']) {
        expect(find.byKey(Key(key)), findsOneWidget, reason: key);
      }
      // Dense: the four totals share a row on a desktop
      final tops = {for (final s in ActivityStatus.values) tester.getTopLeft(find.byKey(Key('total-${s.name}'))).dy.round()};
      expect(tops.length, 1);
      // A row of a full activity on a desktop is a single band: its status block sits beside its content
      final row = tester.getRect(find.byKey(const Key('supervision-item-a1')));
      expect(row.height, lessThan(150));
      final block = tester.getRect(find.descendant(of: find.byKey(const Key('supervision-item-a1')), matching: find.text('Estado al corte')));
      expect(block.left, greaterThan(row.left + row.width / 2), reason: 'the status block is on the right half of the row');
    });

    testWidgets('the status at the cut and the current status are two lines with their own words, never one in place of the other', (tester) async {
      await openSupervision(tester, richRig());
      final a1 = find.byKey(const Key('supervision-item-a1'));
      final cut = find.descendant(of: a1, matching: find.text('Estado al corte'));
      final current = find.descendant(of: a1, matching: find.byKey(const Key('current-status-label')));
      expect(cut, findsOneWidget);
      expect(current, findsOneWidget);
      expect(tester.widget<Text>(current).data, 'Estado actual');
      expect(tester.getTopLeft(cut).dy, lessThan(tester.getTopLeft(current).dy), reason: 'the cut first, the current status apart and after it');
      expect(find.descendant(of: a1, matching: find.text('Bloqueada')), findsOneWidget);
      expect(find.descendant(of: a1, matching: find.text('Completada')), findsOneWidget);
      // Without a status at the cut it says so in words; the current status is not put in its place
      final a5 = find.byKey(const Key('supervision-item-a5'));
      expect(find.descendant(of: a5, matching: find.text('No disponible')), findsOneWidget);
      expect(find.descendant(of: a5, matching: find.byKey(const Key('current-status-label'))), findsNothing);
      // The one that has no current status line says nothing about it
      final a2 = find.byKey(const Key('supervision-item-a2'));
      expect(find.descendant(of: a2, matching: find.text('Estado al corte')), findsOneWidget);
      expect(find.descendant(of: a2, matching: find.text('Estado actual')), findsNothing);
    });

    testWidgets('the history of an activity is one tap away, and the current status is told apart there too', (tester) async {
      final rig = richRig();
      await openSupervision(tester, rig);
      expect(find.byKey(const Key('supervision-open-a1')), findsOneWidget);
      expect(find.byKey(const Key('supervision-open-a3')), findsOneWidget);
      await tapKey(tester, 'supervision-open-a1');
      expect(rig.supervision.historyRequests, ['a1']);
      expect(find.byKey(const Key('supervision-activity')), findsOneWidget);
      expect(find.text('Estado actual'), findsOneWidget);
      expect(find.byKey(const Key('supervision-readonly-note')), findsOneWidget);
      expect(find.byKey(const Key('supervision-audit')), findsOneWidget);
      await tapKey(tester, 'supervision-activity-back');
      expect(find.byKey(const Key('supervision-result')), findsOneWidget, reason: 'coming back keeps the period');
    });

    testWidgets('nothing is asked until the supervisor asks; none, empty and failed are different messages', (tester) async {
      final rig = richRig();
      await openSupervision(tester, rig, submit: false);
      expect(find.byKey(const Key('supervision-none')), findsOneWidget);
      expect(rig.supervision.supervisionRequests, isEmpty);
      expect(find.byKey(const Key('supervision-hint')), findsOneWidget);
      expect(find.textContaining('«al corte»'), findsOneWidget);

      final empty = Rig(supervision: FakeSupervisionRepository());
      await openSupervision(tester, empty);
      expect(find.byKey(const Key('supervision-empty')), findsOneWidget);
      expect(find.byKey(const Key('supervision-totals')), findsOneWidget, reason: 'the totals are still told, with their zeros');

      final down = Rig(supervision: FakeSupervisionRepository()..supervisionError = const ApiError(code: ApiError.network, message: 'Sin conexión'));
      await openSupervision(tester, down);
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
      expect(find.byKey(const Key('supervision-result')), findsNothing);
    });
  });

  group('no overflow', () {
    for (final (name, size, scale) in [
      ('desktop 1400', desktop, 1.0),
      ('tablet 900', tablet, 1.0),
      ('mobile 400', mobile, 1.0),
      ('mobile 400 with text at 1.5', mobile, 1.5),
    ]) {
      testWidgets('Mi equipo fits on $name: logbook, history and its states', (tester) async {
        final rig = richRig();
        await openTeam(tester, rig, size: size, textScale: scale);
        expect(tester.takeException(), isNull);
        await choose(tester, 'peer-select', 'Sara Supervisora');
        expect(tester.takeException(), isNull);
        await choose(tester, 'peer-select', 'Ana Compañera');
        await tapKey(tester, 'peer-submit');
        expect(find.byKey(const Key('peer-logbook')), findsOneWidget);
        expect(tester.takeException(), isNull);
        await showHistory(tester);
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'history-submit');
        expect(find.byKey(const Key('history-list')), findsOneWidget);
        expect(tester.takeException(), isNull);
        // The range error text is the longest message of the form
        await tapKey(tester, 'history-to');
        await tester.tap(find.byTooltip('Previous month'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('30').last);
        await tester.tap(find.text('OK'));
        await tester.pumpAndSettle();
        await tapKey(tester, 'history-submit');
        expect(find.text('La fecha inicial no puede ser posterior a la final.'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });

      testWidgets('Supervisión fits on $name: period, summary, rows and the history of an activity', (tester) async {
        final rig = richRig();
        await openSupervision(tester, rig, size: size, textScale: scale, submit: false);
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'supervision-submit');
        expect(find.byKey(const Key('supervision-result')), findsOneWidget);
        expect(tester.takeException(), isNull);
        for (final id in ['a5', 'a2', 'a3']) {
          await tester.ensureVisible(find.byKey(Key('supervision-item-$id')));
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull, reason: id);
        }
        for (final id in ['a1', 'a2', 'a3']) {
          await tapKey(tester, 'supervision-open-$id');
          expect(tester.takeException(), isNull, reason: 'history of $id');
          await tapKey(tester, 'supervision-activity-back');
        }
        // The period error text
        await tapKey(tester, 'supervision-to');
        await tester.tap(find.byTooltip('Previous month'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('30').last);
        await tester.tap(find.text('OK'));
        await tester.pumpAndSettle();
        await tapKey(tester, 'supervision-submit');
        expect(find.text('La fecha inicial no puede ser posterior a la final.'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });

  group('no rankings, percentages or clock times', () {
    testWidgets('Mi equipo: the list, a logbook and the history', (tester) async {
      await openTeam(tester, richRig());
      expectNoRankingPercentOrClock(tester);
      await choose(tester, 'peer-select', 'Ana Compañera');
      await tapKey(tester, 'peer-submit');
      expect(find.byKey(const Key('peer-logbook')), findsOneWidget);
      expectNoRankingPercentOrClock(tester);
      await showHistory(tester);
      await tapKey(tester, 'history-submit');
      expect(find.byKey(const Key('history-list')), findsOneWidget);
      expectNoRankingPercentOrClock(tester);
    });

    testWidgets('Supervisión: the summary, the rows and the history of an activity', (tester) async {
      await openSupervision(tester, richRig());
      expect(find.byKey(const Key('supervision-result')), findsOneWidget);
      expectNoRankingPercentOrClock(tester);
      // No search and no filter by person: the only inputs are the two dates
      expect(find.byType(TextField), findsNothing);
      expect(find.byType(DropdownButton<String>), findsNothing);
      await tapKey(tester, 'supervision-open-a1');
      expectNoRankingPercentOrClock(tester);
    });
  });
}
