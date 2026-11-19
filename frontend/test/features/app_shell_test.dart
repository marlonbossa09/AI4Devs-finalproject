import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/widgets/buttons.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/features/logbook/presentation/providers/nav_structure.dart';
import 'package:smartwork/features/logbook/presentation/providers/navigation.dart';
import 'package:smartwork/features/logbook/presentation/providers/side_panel.dart';
import 'package:smartwork/features/logbook/presentation/providers/unsaved_changes.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// UX-T2: the frame of the signed-in area (grouped sidebar, 56 px top bar, breadcrumb, active entry of sub-pages) and the side-panel
/// infrastructure. The panel here holds a throw-away field, never a feature form: nothing of Nueva actividad exists yet.
const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

Future<void> pumpApp(WidgetTester tester, {Role role = Role.collaborator, Size size = desktop, FakeLogbookRepository? logbook}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(session: sampleSession(role: role))),
        logbookRepositoryProvider.overrideWithValue(logbook ?? (FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras'))),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  await tester.pumpAndSettle();
}

ProviderContainer containerOf(WidgetTester tester) => ProviderScope.containerOf(tester.element(find.byType(SmartworkApp)));

Finder nav(String key) => find.byKey(Key('nav-$key'));

bool isSelected(WidgetTester tester, String key) => tester.getSemantics(nav(key)).flagsCollection.isSelected;

/// The first widget whose key is a string starting with [prefix] (the fake server numbers its activities itself).
Finder keyed(String prefix) => find.byWidgetPredicate((w) => w.key is ValueKey<String> && (w.key as ValueKey<String>).value.startsWith(prefix)).first;

Future<void> tapFirst(WidgetTester tester, String prefix) async {
  final finder = keyed(prefix);
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Whether the focused widget is inside the widget that has [key].
bool focusIsInside(String key) {
  var inside = false;
  FocusManager.instance.primaryFocus?.context?.visitAncestorElements((element) {
    if (element.widget.key == Key(key)) inside = true;
    return !inside;
  });
  return inside;
}

Finder crumb(String text) => find.descendant(of: find.byKey(const Key('breadcrumb')), matching: find.text(text));

Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// A field that registers its unsaved text with the same guard as every other editor of the app.
class _DirtyField extends ConsumerStatefulWidget {
  const _DirtyField();

  @override
  ConsumerState<_DirtyField> createState() => _DirtyFieldState();
}

class _DirtyFieldState extends ConsumerState<_DirtyField> {
  final _controller = TextEditingController();
  late final UnsavedGuard _guard;

  bool _dirty() => _controller.text.isNotEmpty;

  @override
  void initState() {
    super.initState();
    _guard = ref.read(unsavedGuardProvider);
    _guard.register(_dirty);
  }

  @override
  void dispose() {
    _guard.unregister(_dirty);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => TextField(key: const Key('panel-field'), controller: _controller);
}

SidePanelRequest testPanel({bool withActions = true}) => SidePanelRequest(
  title: 'Panel de prueba',
  subtitle: 'Solo infraestructura',
  icon: Icons.add,
  bodyBuilder: (context) => const Column(children: [_DirtyField(), SizedBox(height: 1800), Text('final del contenido', key: Key('panel-last'))]),
  actionsBuilder: withActions ? (context) => Row(children: [SecondaryButton(key: const Key('panel-cancel'), label: 'Cancelar', onPressed: () {})]) : null,
);

Future<void> openPanel(WidgetTester tester, {bool withActions = true}) async {
  containerOf(tester).read(sidePanelProvider.notifier).open(testPanel(withActions: withActions));
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(loadTestFonts);

  group('sidebar', () {
    testWidgets('a collaborator sees three groups and none of the supervision entries', (tester) async {
      await pumpApp(tester);
      for (final caption in ['MI TRABAJO', 'COLABORACIÓN', 'INFORMES']) {
        expect(find.text(caption), findsOneWidget);
      }
      for (final key in ['dashboard', 'logbook', 'activities', 'planning', 'team', 'report']) {
        expect(nav(key), findsOneWidget, reason: key);
      }
      expect(nav('supervision'), findsNothing);
      expect(nav('team-report'), findsNothing);
    });

    testWidgets('a supervisor also sees the supervision and the team report, in their groups', (tester) async {
      await pumpApp(tester, role: Role.supervisor);
      expect(nav('supervision'), findsOneWidget);
      expect(nav('team-report'), findsOneWidget);
      // each entry sits under its caption, in order: MI TRABAJO < Mi equipo < Supervisión < INFORMES < Informe individual < Informe del equipo
      double y(Finder f) => tester.getTopLeft(f).dy;
      expect(y(find.text('MI TRABAJO')), lessThan(y(nav('dashboard'))));
      expect(y(nav('planning')), lessThan(y(find.text('COLABORACIÓN'))));
      expect(y(find.text('COLABORACIÓN')), lessThan(y(nav('team'))));
      expect(y(nav('team')), lessThan(y(nav('supervision'))));
      expect(y(nav('supervision')), lessThan(y(find.text('INFORMES'))));
      expect(y(find.text('INFORMES')), lessThan(y(nav('report'))));
      expect(y(nav('report')), lessThan(y(nav('team-report'))));
    });

    testWidgets('it offers nothing the product does not have: no settings, no notifications, no search', (tester) async {
      await pumpApp(tester, role: Role.supervisor);
      expect(find.text('Configuración'), findsNothing);
      expect(find.text('MI CUENTA'), findsNothing);
      expect(find.byTooltip('Notificaciones no disponibles'), findsNothing);
      expect(find.byIcon(Icons.search), findsNothing);
    });

    testWidgets('the foot shows who is signed in, the role and Cerrar sesión', (tester) async {
      await pumpApp(tester);
      expect(find.byKey(const Key('who')), findsOneWidget);
      expect(find.byKey(const Key('role')), findsOneWidget);
      expect(find.byKey(const Key('logout')), findsOneWidget);
      expect(find.text('Cerrar sesión'), findsOneWidget);
    });

    testWidgets('sizes: 232 px on a desktop, 208 px on a tablet, entries at least 40 px tall', (tester) async {
      await pumpApp(tester);
      expect(tester.getSize(nav('dashboard')).width, closeTo(232 - 24, 1));
      expect(tester.getSize(nav('dashboard')).height, greaterThanOrEqualTo(40));
      await pumpApp(tester, size: tablet);
      expect(tester.getSize(nav('dashboard')).width, closeTo(208 - 24, 1));
    });

    testWidgets('the current entry is announced as selected and the others are not', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      expect(isSelected(tester, 'dashboard'), isTrue);
      expect(isSelected(tester, 'logbook'), isFalse);
      await tapKey(tester, 'nav-logbook');
      expect(isSelected(tester, 'logbook'), isTrue);
      expect(isSelected(tester, 'dashboard'), isFalse);
      handle.dispose();
    });

    testWidgets('it can be used with the keyboard alone: Tab reaches the entries in order and Enter opens one', (tester) async {
      await pumpApp(tester);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab); // Panel principal
      await tester.sendKeyEvent(LogicalKeyboardKey.tab); // Mi bitácora
      await tester.pump();
      expect(focusIsInside('nav-logbook'), isTrue);
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('work-date')), findsOneWidget); // Mi bitácora
    });

    testWidgets('the tab order walks the whole sidebar first (entries, then Cerrar sesión) and then the page', (tester) async {
      await pumpApp(tester); // a collaborator: 6 entries + Cerrar sesión
      final order = <String>[];
      for (var i = 0; i < 8; i++) {
        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        String? found;
        FocusManager.instance.primaryFocus?.context?.visitAncestorElements((element) {
          final key = element.widget.key;
          if (key is ValueKey<String> && (key.value.startsWith('nav-') || key.value == 'logout' || key.value.startsWith('dashboard-'))) {
            found = key.value;
            return false;
          }
          return true;
        });
        order.add(found ?? '?');
      }
      expect(order.take(7), ['nav-dashboard', 'nav-logbook', 'nav-activities', 'nav-planning', 'nav-team', 'nav-report', 'logout']);
      expect(order[7], isNot(startsWith('nav-'))); // only then the top bar and the page
    });

    testWidgets('on a phone it is a drawer with the same groups, opened from the top bar and closed when an entry is chosen', (tester) async {
      await pumpApp(tester, size: mobile, role: Role.supervisor);
      expect(nav('dashboard'), findsNothing);
      await tester.tap(find.byKey(const Key('menu-toggle')));
      await tester.pumpAndSettle();
      expect(find.text('MI TRABAJO'), findsOneWidget);
      expect(nav('supervision'), findsOneWidget);
      await tester.tap(nav('team'));
      await tester.pumpAndSettle();
      expect(nav('team'), findsNothing); // the drawer closed
      expect(find.byKey(const Key('peer-none')).evaluate().isNotEmpty || find.byKey(const Key('team-mode')).evaluate().isNotEmpty, isTrue);
    });
  });

  group('top bar', () {
    testWidgets('it is 56 px tall and shows the breadcrumb and the server date, no bell and no avatar', (tester) async {
      await pumpApp(tester);
      expect(tester.getSize(find.byKey(const Key('topbar'))).height, 56);
      expect(find.byKey(const Key('breadcrumb')), findsOneWidget);
      expect(find.byKey(const Key('top-date')), findsOneWidget);
      expect(find.byIcon(Icons.notifications_none_outlined), findsNothing);
    });

    testWidgets('on a phone it keeps the menu button and the breadcrumb, without the date, in 56 px', (tester) async {
      await pumpApp(tester, size: mobile);
      expect(tester.getSize(find.byKey(const Key('topbar'))).height, 56);
      expect(find.byKey(const Key('menu-toggle')), findsOneWidget);
      expect(find.byKey(const Key('top-date')), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });

  group('breadcrumb and active entry of sub-pages', () {
    testWidgets('a top-level page is not repeated in the breadcrumb: the title is the page\'s own', (tester) async {
      await pumpApp(tester);
      expect(crumb('Mi espacio'), findsOneWidget);
      expect(crumb('Mi trabajo'), findsOneWidget);
      expect(crumb('Panel principal'), findsNothing);
    });

    testWidgets('the detail of an activity opened from Actividades keeps Actividades highlighted and links back to it', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      await tapKey(tester, 'nav-activities');
      await tapFirst(tester, 'activity-row-');
      expect(isSelected(tester, 'activities'), isTrue);
      expect(crumb('Actividades'), findsOneWidget);
      expect(crumb('Detalle de actividad'), findsOneWidget);
      await tester.tap(crumb('Actividades')); // the parent is a link to where you came from
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('activities-new-planning')), findsOneWidget);
      expect(isSelected(tester, 'activities'), isTrue);
      handle.dispose();
    });

    testWidgets('the detail opened from the dashboard keeps THE DASHBOARD highlighted (where the person came from), not another entry', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      await tapFirst(tester, 'activity-open-');
      expect(isSelected(tester, 'dashboard'), isTrue);
      expect(isSelected(tester, 'activities'), isFalse);
      expect(crumb('Panel principal'), findsOneWidget);
      expect(crumb('Detalle de actividad'), findsOneWidget);
      handle.dispose();
    });

    testWidgets('recording an unplanned activity belongs to Mi bitácora', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      await tapKey(tester, 'dashboard-new-unplanned');
      expect(isSelected(tester, 'logbook'), isTrue);
      expect(crumb('Mi bitácora'), findsOneWidget);
      expect(crumb('Actividad no planificada'), findsOneWidget);
      handle.dispose();
    });

    testWidgets('a deeper page (the audit of an activity) shows the whole path and keeps the origin highlighted', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      await tapKey(tester, 'nav-activities');
      await tapFirst(tester, 'activity-row-');
      await tapKey(tester, 'detail-audit');
      expect(crumb('Detalle de actividad'), findsOneWidget);
      expect(crumb('Historial de auditoría'), findsOneWidget);
      expect(isSelected(tester, 'activities'), isTrue);
      handle.dispose();
    });
  });

  group('navigation structure (pure)', () {
    test('every page has a name and every top-level page a group', () {
      for (final page in AppPage.values) {
        expect(pageNames[page], isNotNull, reason: '$page');
      }
      expect(topLevelSection[AppPage.dashboard], NavSection.work);
      expect(topLevelSection[AppPage.team], NavSection.collaboration);
      expect(topLevelSection[AppPage.teamReport], NavSection.reports);
    });

    test('a page without an entry resolves to the top-level page its origins end in', () {
      AppPage? back(AppPage p) => switch (p) {
        AppPage.correction => AppPage.activityDetail,
        AppPage.activityDetail => AppPage.logbook,
        _ => null,
      };
      expect(navItemFor(AppPage.correction, back), AppPage.logbook);
      expect(navItemFor(AppPage.activityDetail, (_) => null), AppPage.activities);
      expect(navItemFor(AppPage.supervisionActivity, (_) => null), AppPage.supervision);
      expect(navItemFor(AppPage.unplanned, (_) => null), AppPage.logbook);
      expect(navItemFor(AppPage.team, (_) => null), AppPage.team);
    });

    test('a loop of origins cannot hang the navigation', () {
      expect(navItemFor(AppPage.progress, (p) => AppPage.continuation), isIn(topLevelSection.keys));
    });
  });

  group('side panel (infrastructure, no form)', () {
    testWidgets('it opens over the content with its title, subtitle, close button and actions, under the top bar', (tester) async {
      await pumpApp(tester);
      expect(find.byKey(const Key('side-panel')), findsNothing);
      await openPanel(tester);
      expect(find.byKey(const Key('side-panel')), findsOneWidget);
      expect(find.text('Panel de prueba'), findsOneWidget);
      expect(find.text('Solo infraestructura'), findsOneWidget);
      expect(find.byKey(const Key('side-panel-close')), findsOneWidget);
      expect(find.byKey(const Key('side-panel-actions')), findsOneWidget);
      expect(tester.getSize(find.byKey(const Key('side-panel'))).width, 480);
      expect(tester.getTopLeft(find.byKey(const Key('side-panel'))).dy, 56); // right under the top bar
    });

    testWidgets('it takes the whole width on a phone', (tester) async {
      await pumpApp(tester, size: mobile);
      await openPanel(tester);
      expect(tester.getSize(find.byKey(const Key('side-panel'))).width, 400);
      expect(tester.takeException(), isNull);
    });

    testWidgets('its body scrolls on its own: the page behind does not move', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      final pageTop = tester.getTopLeft(find.text('Buen día, Carlos')).dy;
      expect(tester.getTopLeft(find.byKey(const Key('panel-last'))).dy, greaterThan(1000)); // below the screen
      await tester.drag(find.byKey(const Key('side-panel-body')), const Offset(0, -2000));
      await tester.pumpAndSettle();
      expect(tester.getTopLeft(find.byKey(const Key('panel-last'))).dy, lessThan(1000));
      expect(tester.getTopLeft(find.text('Buen día, Carlos')).dy, pageTop);
      // the actions stay pinned
      expect(find.byKey(const Key('panel-cancel')), findsOneWidget);
    });

    testWidgets('it closes with its button, with Escape and with a tap outside, when nothing was typed', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      await tester.tap(find.byKey(const Key('side-panel-close')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsNothing);

      await openPanel(tester);
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsNothing);

      await openPanel(tester);
      await tester.tapAt(const Offset(300, 400)); // the dimmed area outside the panel
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsNothing);
      expect(find.byKey(const Key('confirm-title')), findsNothing); // no question: nothing would be lost
    });

    testWidgets('the focus starts in the panel and goes back to what had it when it closes', (tester) async {
      await pumpApp(tester);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab); // the keyboard reaches the first sidebar entry
      await tester.pump();
      final before = FocusManager.instance.primaryFocus;
      expect(before, isNotNull);
      expect(focusIsInside('nav-dashboard'), isTrue);
      await openPanel(tester);
      await tester.pump();
      expect(focusIsInside('side-panel'), isTrue); // the focus went into the panel
      expect(FocusManager.instance.primaryFocus, isNot(same(before)));
      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();
      expect(FocusManager.instance.primaryFocus, same(before));
    });

    testWidgets('while it is open the page behind it is out of reach of the keyboard and of assistive technology', (tester) async {
      final closed = find.byWidgetPredicate((w) => w is ExcludeFocus && w.excluding).evaluate().length;
      await pumpApp(tester);
      final before = find.byWidgetPredicate((w) => w is ExcludeFocus && w.excluding).evaluate().length;
      expect(before, closed);
      await openPanel(tester);
      expect(find.byWidgetPredicate((w) => w is ExcludeFocus && w.excluding).evaluate().length, before + 1);
      expect(find.byWidgetPredicate((w) => w is ExcludeSemantics && w.excluding).evaluate().length, greaterThanOrEqualTo(1));
    });

    testWidgets('it is announced with its name, and its title is a heading', (tester) async {
      final handle = tester.ensureSemantics();
      await pumpApp(tester);
      await openPanel(tester);
      final node = tester.getSemantics(find.byKey(const Key('side-panel')));
      expect(node.label, contains('Panel de prueba'));
      expect(node.flagsCollection.namesRoute, isTrue);
      handle.dispose();
    });

    testWidgets('with typed text it asks before closing: "Seguir editando" keeps it open and "Descartar cambios" closes it', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      await tester.enterText(find.byKey(const Key('panel-field')), 'algo escrito');
      await tester.tap(find.byKey(const Key('side-panel-close')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-keep')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsOneWidget);
      expect(tester.widget<TextField>(find.byKey(const Key('panel-field'))).controller!.text, 'algo escrito');

      await tester.sendKeyEvent(LogicalKeyboardKey.escape); // Escape asks the same question
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsNothing);
    });

    testWidgets('changing page with typed text asks first; discarding changes the page and closes the panel', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      await tester.enterText(find.byKey(const Key('panel-field')), 'algo escrito');
      await tester.tap(nav('logbook'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-keep')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsOneWidget);
      expect(find.text('Buen día, Carlos'), findsOneWidget); // still the dashboard

      await tester.tap(nav('logbook'));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsNothing);
      expect(find.byKey(const Key('work-date')), findsOneWidget);
    });

    testWidgets('changing page without typed text closes the panel at once', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      await tester.tap(nav('team'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('side-panel')), findsNothing);
      expect(find.byKey(const Key('confirm-title')), findsNothing);
    });

    testWidgets('signing out with typed text asks first; without it, the session ends and no panel survives it', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      await tester.enterText(find.byKey(const Key('panel-field')), 'algo escrito');
      await tester.tap(find.byKey(const Key('logout')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-discard')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(containerOf(tester).read(sidePanelProvider), isNull);
    });

    testWidgets('opening another panel while one holds typed text asks first', (tester) async {
      await pumpApp(tester);
      await openPanel(tester);
      await tester.enterText(find.byKey(const Key('panel-field')), 'algo escrito');
      containerOf(tester).read(sidePanelProvider.notifier).open(SidePanelRequest(title: 'Otro', bodyBuilder: (context) => const Text('otro')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('confirm-title')), findsOneWidget);
      await tester.tap(find.byKey(const Key('confirm-keep')));
      await tester.pumpAndSettle();
      expect(find.text('Panel de prueba'), findsOneWidget);
    });
  });

  group('unsaved guard with several editors', () {
    test('it asks when ANY registered editor holds text, and forgets an editor that is removed', () {
      final guard = UnsavedGuard();
      var summary = false, panel = false;
      bool a() => summary;
      bool b() => panel;
      guard.register(a);
      guard.register(b);
      expect(guard.hasUnsaved, isFalse);
      panel = true;
      expect(guard.hasUnsaved, isTrue); // the second editor no longer replaces the first
      panel = false;
      summary = true;
      expect(guard.hasUnsaved, isTrue);
      guard.unregister(a);
      expect(guard.hasUnsaved, isFalse);
      guard.register(a);
      guard.register(a); // registering the same check twice does not duplicate it
      guard.unregister(a);
      expect(guard.hasUnsaved, isFalse);
    });
  });
}
