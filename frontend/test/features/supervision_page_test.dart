import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/core/widgets/status_pill.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/audit_entities.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/pages/home_page.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/supervision/domain/entities/supervision_entities.dart';
import 'package:smartwork/features/supervision/presentation/providers/supervision_repository.dart';
import 'package:smartwork/features/team/domain/entities/team_entities.dart';
import 'package:smartwork/features/team/presentation/providers/team_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';
import '../helpers/supervision_fakes.dart';
import '../helpers/team_fakes.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

class Setup {
  Setup({FakeSupervisionRepository? supervision, FakeLogbookRepository? logbook})
    : supervision = supervision ?? FakeSupervisionRepository(),
      logbook = logbook ?? FakeLogbookRepository(),
      team = FakeTeamRepository();

  final FakeSupervisionRepository supervision;
  final FakeLogbookRepository logbook;
  final FakeTeamRepository team;
}

Future<void> pumpApp(WidgetTester tester, Setup s, {Role role = Role.supervisor, Size size = desktop}) async {
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

Future<void> openSupervision(WidgetTester tester, Setup s, {Size size = desktop, bool submit = true}) async {
  await pumpApp(tester, s, size: size);
  await tapKey(tester, 'nav-supervision');
  if (submit) await tapKey(tester, 'supervision-submit');
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

int _n = 0;

AuditEntry auditEntry(String objectId, String reason) => AuditEntry(
  id: 'e${++_n}',
  moment: DateTime.utc(2026, 11, 6, 10, _n),
  operationName: 'marca_error',
  operation: AuditOperation.errorMark,
  objectType: 'actividad',
  objectId: objectId,
  authorId: 'p2',
  workDate: DateTime.utc(2026, 11, 5),
  reason: reason,
);

FakeSupervisionRepository withItems() => FakeSupervisionRepository()
  ..items = [
    supervised('a1', 'Informe mensual', reasons: [InclusionReason.plannedInPeriod, InclusionReason.pendingAtCut], atCut: ActivityStatus.blocked, currentIfDiffers: ActivityStatus.completed),
    supervised('a5', 'Sin estado al corte visible', atCut: null),
    supervisedNeutral('a2', atCut: ActivityStatus.inProgress),
    minimalReference('a3', owner: 'p3', last: DateTime.utc(2026, 11, 4)),
  ];

void main() {
  setUpAll(loadTestFonts);

  group('navigation and roles', () {
    testWidgets('a supervisor is offered "Supervisión"; a collaborator is not, but keeps "Mi equipo"', (tester) async {
      await pumpApp(tester, Setup(), role: Role.supervisor);
      expect(find.byKey(const Key('nav-supervision')), findsOneWidget);
      expect(find.byKey(const Key('nav-team')), findsOneWidget);
      await pumpApp(tester, Setup(), role: Role.collaborator);
      expect(find.byKey(const Key('nav-supervision')), findsNothing);
      expect(find.byKey(const Key('nav-team')), findsOneWidget);
    });

    testWidgets('a collaborator who somehow reaches the page sees it unavailable and nothing is asked of the server', (tester) async {
      final s = Setup();
      await pumpApp(tester, s, role: Role.collaborator);
      ProviderScope.containerOf(tester.element(find.byType(HomePage))).read(currentPageProvider.notifier).go(AppPage.supervision);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('supervision-not-available')), findsOneWidget);
      expect(find.byKey(const Key('supervision-submit')), findsNothing);
      expect(s.supervision.supervisionRequests, isEmpty);
    });

    testWidgets('losing the role is answered by the server: the screen shows the fixed message and no data', (tester) async {
      final s = Setup(supervision: withItems()..supervisionError = const ApiError(code: 'OPERACION_NO_PERMITIDA', message: 'PAYLOAD'));
      await openSupervision(tester, s);
      expect(find.textContaining('no está permitida para tu rol'), findsOneWidget);
      expect(find.textContaining('PAYLOAD'), findsNothing);
      expect(find.byKey(const Key('supervision-result')), findsNothing);
    });
  });

  group('the consolidated view (M4-03)', () {
    testWidgets('asks only when the supervisor asks, always with a period; shows the cut, the totals and the count apart', (tester) async {
      final s = Setup(supervision: withItems());
      await openSupervision(tester, s, submit: false);
      expect(find.byKey(const Key('supervision-none')), findsOneWidget);
      expect(s.supervision.supervisionRequests, isEmpty);
      await tapKey(tester, 'supervision-submit');
      final request = s.supervision.supervisionRequests.single;
      expect(request['from'], addDays(today, -6));
      expect(request['to'], today);
      expect(request['cursor'], isNull);
      expect(find.textContaining('Corte: ${formatShortDate(today)}'), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('total-inProgress')), matching: find.text('2')), findsOneWidget);
      expect(find.descendant(of: find.byKey(const Key('total-completed')), matching: find.text('1')), findsOneWidget);
      expect(find.textContaining('Sin estado al corte: 1 referencias mínimas y 1 actividades'), findsOneWidget);
      expect(find.textContaining('No están en los totales'), findsOneWidget);
      expectNoRanking();
      expectReadOnly();
    });

    testWidgets('the status at the cut and the current status are told apart; an omitted status at the cut is not inferred', (tester) async {
      await openSupervision(tester, Setup(supervision: withItems()..pageSize = 10));
      final a1 = find.byKey(const Key('supervision-item-a1'));
      expect(find.descendant(of: a1, matching: find.text('Estado al corte')), findsOneWidget);
      expect(find.descendant(of: a1, matching: find.text('Bloqueada')), findsOneWidget);
      expect(find.descendant(of: a1, matching: find.byKey(const Key('current-status-label'))), findsOneWidget);
      expect(find.descendant(of: a1, matching: find.text('Completada')), findsOneWidget, reason: 'shown apart, as the current status');
      expect(find.descendant(of: a1, matching: find.text('Planificada en el período')), findsOneWidget);
      expect(find.descendant(of: a1, matching: find.text('Pendiente al corte')), findsOneWidget);
      final a5 = find.byKey(const Key('supervision-item-a5'));
      expect(find.descendant(of: a5, matching: find.byKey(const Key('status-at-cut-unavailable'))), findsOneWidget);
      expect(find.descendant(of: a5, matching: find.byKey(const Key('current-status-label'))), findsNothing, reason: 'the current status is not put in its place');
      expect(find.descendant(of: a5, matching: find.byType(StatusPill)), findsNothing);
    });

    testWidgets('a full activity, a neutral one and a minimal reference are three different things', (tester) async {
      await openSupervision(tester, Setup(supervision: withItems()..pageSize = 10));
      expect(find.text('Informe mensual'), findsOneWidget);
      final neutral = find.byKey(const Key('supervision-item-a2'));
      expect(find.descendant(of: neutral, matching: find.text('Actividad en continuidad')), findsOneWidget);
      final reference = find.byKey(const Key('supervision-item-a3'));
      expect(find.descendant(of: reference, matching: find.text('REFERENCIA MÍNIMA')), findsOneWidget);
      expect(find.descendant(of: reference, matching: find.text('Iniciada en otro equipo')), findsOneWidget);
      expect(find.descendant(of: reference, matching: find.text('Último avance: 04/11/2026')), findsOneWidget);
      expect(find.descendant(of: reference, matching: find.byKey(const Key('minimal-note'))), findsOneWidget);
      expect(find.descendant(of: reference, matching: find.text('Estado al corte')), findsNothing, reason: 'a minimal reference has no status at the cut');
      expect(find.descendant(of: reference, matching: find.text('Ver referencia')), findsOneWidget);
      expect(find.descendant(of: neutral, matching: find.text('Informe mensual')), findsNothing);
      expectNoRanking();
    });

    testWidgets('follows the server cursor with "Ver más", keeps what is loaded when it fails and repeats nothing', (tester) async {
      final server = withItems()..moreErrors.add(const ApiError(code: ApiError.network, message: 'Sin conexión'));
      await openSupervision(tester, Setup(supervision: server));
      expect(find.byKey(const Key('supervision-item-a5')), findsOneWidget);
      expect(find.byKey(const Key('supervision-item-a2')), findsNothing);
      await tapKey(tester, 'supervision-load-more');
      expect(find.byKey(const Key('supervision-more-error')), findsOneWidget);
      expect(find.byKey(const Key('supervision-item-a1')), findsOneWidget, reason: 'the page already loaded stays');
      await tapKey(tester, 'supervision-load-more');
      expect(server.supervisionRequests.last['cursor'], '2');
      expect(find.byKey(const Key('supervision-item-a2')), findsOneWidget);
      expect(find.byKey(const Key('supervision-item-a3')), findsOneWidget);
      expect(find.byKey(const Key('supervision-item-a1')), findsOneWidget);
      expect(find.byKey(const Key('supervision-load-more')), findsNothing);
    });

    testWidgets('a period that cannot be sent is not sent: end before start, and more than 92 days', (tester) async {
      final s = Setup(supervision: withItems());
      await openSupervision(tester, s, submit: false);
      await tapKey(tester, 'supervision-to');
      await tester.tap(find.byTooltip('Previous month'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('30').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'supervision-submit');
      expect(find.text('La fecha inicial no puede ser posterior a la final.'), findsOneWidget);
      await tapKey(tester, 'supervision-to');
      await tester.tap(find.text('6').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'supervision-from');
      for (var i = 0; i < 4; i++) {
        await tester.tap(find.byTooltip('Previous month'));
        await tester.pumpAndSettle();
      }
      await tester.tap(find.text('1').last);
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      await tapKey(tester, 'supervision-submit');
      expect(find.text('El rango puede abarcar como máximo 92 días.'), findsOneWidget);
      expect(s.supervision.supervisionRequests, isEmpty);
    });

    testWidgets('empty, connection error with retry, and an access error with its own fixed text are different', (tester) async {
      final empty = Setup(supervision: FakeSupervisionRepository());
      await openSupervision(tester, empty);
      expect(find.byKey(const Key('supervision-empty')), findsOneWidget);

      final down = Setup(supervision: withItems()..supervisionError = const ApiError(code: ApiError.network, message: 'Sin conexión'));
      await openSupervision(tester, down);
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
      down.supervision.supervisionError = null;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('supervision-result')), findsOneWidget);

      final off = Setup(supervision: withItems()..supervisionError = const ApiError(code: 'ACCESO_DESACTIVADO', message: 'PAYLOAD'));
      await openSupervision(tester, off);
      expect(find.textContaining('Tu acceso está desactivado'), findsOneWidget);
      expect(find.textContaining('PAYLOAD'), findsNothing);
    });
  });

  group('the history of an activity (M4-04)', () {
    FakeSupervisionRepository withHistories() {
      final server = withItems()..pageSize = 10;
      server.histories['a1'] = ActivityHistoryDetail(
        activity: fullActivity('a1', 'Informe mensual', status: null),
        plannings: [PeerPlanning(activityId: 'a1', date: DateTime.utc(2026, 11, 1), type: PlanningType.original, description: 'Revisar cifras')],
        progress: [
          PeerProgress(activityId: 'a1', date: DateTime.utc(2026, 11, 2), status: ActivityStatus.inProgress, description: 'Primer avance'),
          PeerProgress(activityId: 'a1', date: DateTime.utc(2026, 11, 5), status: ActivityStatus.blocked, description: 'Segundo avance', blockReason: 'Falta el acceso'),
        ],
        currentStatus: ActivityStatus.blocked,
      );
      server.histories['a2'] = ActivityHistoryDetail(
        activity: neutralActivity('a2'),
        plannings: const [],
        progress: [PeerProgress(activityId: 'a2', date: DateTime.utc(2026, 11, 5), status: ActivityStatus.inProgress, description: 'Avance propio de este equipo')],
      );
      server.histories['a3'] = ActivityHistoryReference(minimalReference('a3', owner: 'p3'));
      return server;
    }

    testWidgets('a full activity: authorized plannings and progress in order, the block reason, no way to change anything, and its audit', (tester) async {
      final s = Setup(supervision: withHistories());
      s.logbook.seedAudit(AuditObjectType.activity, 'a1', [auditEntry('a1', 'Duplicada')]);
      await openSupervision(tester, s);
      await tapKey(tester, 'supervision-open-a1');
      expect(s.supervision.historyRequests, ['a1']);
      expect(find.byKey(const Key('supervision-activity')), findsOneWidget);
      expect(find.text('Informe mensual'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      expect(find.textContaining('Motivo del bloqueo: Falta el acceso'), findsOneWidget);
      expect(find.byKey(const Key('history-current-status-label')), findsOneWidget);
      expect(tester.getTopLeft(find.text('Primer avance')).dy, lessThan(tester.getTopLeft(find.text('Segundo avance')).dy), reason: 'historical order, as the server sends it');
      expect(find.byKey(const Key('supervision-readonly-note')), findsOneWidget);
      expectReadOnly();
      expectNoRanking();
      // The audit (M3-07), reused as it is, and back to the same activity
      await tapKey(tester, 'supervision-audit');
      expect(s.logbook.auditRequests.single['type'], AuditObjectType.activity);
      expect(s.logbook.auditRequests.single['objectId'], 'a1');
      expect(find.text('Motivo: Duplicada'), findsOneWidget);
      await tapKey(tester, 'audit-back');
      expect(find.byKey(const Key('supervision-activity')), findsOneWidget);
    });

    testWidgets('a neutral activity stays neutral: no title, no audit link, and no other endpoint is asked to learn more', (tester) async {
      final s = Setup(supervision: withHistories());
      await openSupervision(tester, s);
      await tapKey(tester, 'supervision-open-a2');
      expect(find.byKey(const Key('neutral-label')), findsOneWidget);
      expect(find.text('Avance propio de este equipo'), findsOneWidget);
      expect(find.byKey(const Key('supervision-audit')), findsNothing);
      expect(find.text('Informe mensual'), findsNothing);
      expect(s.supervision.historyRequests, ['a2']);
      expect(s.logbook.auditRequests, isEmpty);
      expect(s.team.logbookRequests, isEmpty);
      expectReadOnly();
    });

    testWidgets('a minimal reference shows only the reference: no plannings, no progress, no audit', (tester) async {
      final s = Setup(supervision: withHistories());
      await openSupervision(tester, s);
      await tapKey(tester, 'supervision-open-a3');
      expect(find.byKey(const Key('minimal-reference-a3')), findsOneWidget);
      expect(find.byKey(const Key('supervision-activity')), findsNothing);
      expect(find.text('Planificaciones'), findsNothing);
      expect(find.byKey(const Key('supervision-audit')), findsNothing);
      expectReadOnly();
    });

    testWidgets('not available is one neutral message, an error can be retried, and going back keeps the period', (tester) async {
      final s = Setup(supervision: withHistories()..histories.remove('a1'));
      await openSupervision(tester, s);
      await tapKey(tester, 'supervision-open-a1');
      expect(find.byKey(const Key('supervision-activity-unavailable')), findsOneWidget);
      s.supervision.historyError = const ApiError(code: ApiError.network, message: 'Sin conexión');
      await tapKey(tester, 'supervision-activity-back');
      expect(find.byKey(const Key('supervision-result')), findsOneWidget, reason: 'the period asked is kept');
      await tapKey(tester, 'supervision-open-a2');
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
    });
  });

  group('layout', () {
    for (final (name, size) in [('mobile', mobile), ('tablet', tablet), ('desktop', desktop)]) {
      testWidgets('the view and the history fit on $name without overflow', (tester) async {
        final server = withItems()..pageSize = 10;
        server.histories['a1'] = ActivityHistoryDetail(
          activity: fullActivity('a1', 'Una actividad con un título largo que ocupa varias líneas en una pantalla estrecha'),
          plannings: [PeerPlanning(activityId: 'a1', date: today, type: PlanningType.original, description: 'Un plan con un texto largo para comprobar el ajuste al ancho disponible')],
          progress: [PeerProgress(activityId: 'a1', date: today, status: ActivityStatus.blocked, description: 'Un avance largo para comprobar el ajuste', blockReason: 'Un motivo largo del bloqueo')],
          currentStatus: ActivityStatus.blocked,
        );
        await openSupervision(tester, Setup(supervision: server), size: size);
        expect(find.byKey(const Key('supervision-result')), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tapKey(tester, 'supervision-open-a1');
        expect(find.byKey(const Key('supervision-activity')), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });
}
