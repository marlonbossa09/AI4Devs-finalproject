import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/app.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/widgets/segmented_control.dart';
import 'package:smartwork/core/widgets/stat_card.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/presentation/providers/logbook_repository.dart';
import 'package:smartwork/main.dart' show noAutomaticRetry;

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

const desktop = Size(1400, 1000);
const tablet = Size(900, 1000);
const mobile = Size(400, 900);

Future<void> pumpApp(
  WidgetTester tester, {
  required FakeAuthRepository auth,
  FakeLogbookRepository? logbook,
  Size size = desktop,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      retry: noAutomaticRetry,
      overrides: [
        authRepositoryProvider.overrideWithValue(auth),
        logbookRepositoryProvider.overrideWithValue(logbook ?? FakeLogbookRepository()),
      ],
      child: const SmartworkApp(webFonts: false),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> go(WidgetTester tester, String page) async {
  await tester.tap(find.byKey(Key('nav-$page')));
  await tester.pumpAndSettle();
}

Future<void> fillPlanning(WidgetTester tester, {String title = 'Preparar informe', String description = ''}) async {
  await tester.enterText(find.byKey(const Key('plan-title')), title);
  if (description.isNotEmpty) {
    await tester.enterText(find.byKey(const Key('plan-description')), description);
  }
}

Future<void> submitPlanning(WidgetTester tester) async {
  await tester.ensureVisible(find.byKey(const Key('plan-submit')));
  await tester.tap(find.byKey(const Key('plan-submit')));
  await tester.pumpAndSettle();
}

Future<void> planFromScreen(WidgetTester tester, {String title = 'Preparar informe', String description = ''}) async {
  await fillPlanning(tester, title: title, description: description);
  await submitPlanning(tester);
}

StatCard stat(WidgetTester tester, String label) =>
    tester.widget<StatCard>(find.byWidgetPredicate((w) => w is StatCard && w.label == label));

String textOf(WidgetTester tester, Key key) => tester.widget<Text>(find.byKey(key)).data!;

FakeAuthRepository signedIn({Role role = Role.collaborator}) => FakeAuthRepository(session: sampleSession(role: role));

void main() {
  setUpAll(loadTestFonts);

  group('login', () {
    testWidgets('without a session nothing of the logbooks is shown (CA-01)', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: FakeAuthRepository(), logbook: logbook);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(find.byKey(const Key('plan-submit')), findsNothing);
      expect(find.byKey(const Key('who')), findsNothing);
      expect(find.byKey(const Key('nav-logbook')), findsNothing);
      expect(logbook.calls, isEmpty);
    });

    testWidgets('invalid credentials show one message that does not say which field failed', (tester) async {
      final auth = FakeAuthRepository(
        loginError: const ApiError(code: 'CREDENCIALES_INVALIDAS', message: 'x', status: 401),
      );
      await pumpApp(tester, auth: auth);
      await tester.enterText(find.byKey(const Key('login-id')), 'ana');
      await tester.enterText(find.byKey(const Key('login-password')), 'mala');
      await tester.tap(find.byKey(const Key('login-submit')));
      await tester.pumpAndSettle();
      expect(find.text('El usuario o la contraseña no son correctos.'), findsOneWidget);
      expect(find.byKey(const Key('nav-logbook')), findsNothing);
      // The password field is cleared after a failure
      expect(tester.widget<TextField>(find.byKey(const Key('login-password'))).controller!.text, isEmpty);
    });

    testWidgets('empty fields are not sent', (tester) async {
      final auth = FakeAuthRepository();
      await pumpApp(tester, auth: auth);
      await tester.tap(find.byKey(const Key('login-submit')));
      await tester.pumpAndSettle();
      expect(auth.loginAttempts, isEmpty);
      expect(find.text('Escribe tu usuario y tu contraseña.'), findsOneWidget);
    });

    testWidgets('a disabled access is explained after login', (tester) async {
      final auth = FakeAuthRepository(
        loginError: const ApiError(code: 'ACCESO_DESACTIVADO', message: 'x', status: 403),
      );
      await pumpApp(tester, auth: auth);
      await tester.enterText(find.byKey(const Key('login-id')), 'ana');
      await tester.enterText(find.byKey(const Key('login-password')), 'contraseña-correcta');
      await tester.tap(find.byKey(const Key('login-submit')));
      await tester.pumpAndSettle();
      expect(find.textContaining('acceso está desactivado'), findsOneWidget);
    });

    testWidgets('a valid login shows the user, the role and the server date', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: FakeAuthRepository(), logbook: logbook);
      await tester.enterText(find.byKey(const Key('login-id')), 'colaborador1.demo');
      await tester.enterText(find.byKey(const Key('login-password')), 'contraseña-correcta');
      await tester.tap(find.byKey(const Key('login-submit')));
      await tester.pumpAndSettle();
      expect(textOf(tester, const Key('who')), 'Carlos Colaborador (demo)');
      expect(textOf(tester, const Key('role')), 'Colaborador');
      expect(textOf(tester, const Key('top-date')), 'Viernes, 6 de noviembre de 2026');
      expect(logbook.calls, ['get 2026-11-06']); // the date comes from the server, not the device
    });

    testWidgets('an existing session is recovered at startup', (tester) async {
      await pumpApp(tester, auth: signedIn(role: Role.supervisor));
      expect(textOf(tester, const Key('role')), 'Supervisor');
    });

    testWidgets('logging out goes back to the login', (tester) async {
      final auth = signedIn();
      await pumpApp(tester, auth: auth);
      await tester.tap(find.byKey(const Key('logout')));
      await tester.pumpAndSettle();
      expect(auth.logoutCalls, 1);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(find.byKey(const Key('who')), findsNothing);
    });

    testWidgets('desktop shows the brand panel; mobile hides its long text', (tester) async {
      await pumpApp(tester, auth: FakeAuthRepository());
      expect(find.textContaining('Un espacio simple para planificar'), findsOneWidget);
      expect(find.text('Inicia sesión'), findsOneWidget);
      await pumpApp(tester, auth: FakeAuthRepository(), size: mobile);
      expect(find.textContaining('Un espacio simple para planificar'), findsNothing);
      expect(find.text('Inicia sesión'), findsOneWidget);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
  });

  group('dashboard', () {
    testWidgets('greets the user by first name and starts on the dashboard', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(find.text('Mi jornada'), findsOneWidget);
      expect(find.byKey(const Key('breadcrumb')), findsOneWidget);
      expect(find.textContaining('Panel principal'), findsWidgets);
    });

    testWidgets('the indicators are computed from what the server holds for the date', (tester) async {
      final logbook = FakeLogbookRepository()
        ..seed(today, 'Una')
        ..seed(today, 'Dos')
        ..seed(today, 'Tres', status: ActivityStatus.inProgress)
        ..seed(today, 'Cuatro', status: ActivityStatus.completed);
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      expect(stat(tester, 'Total de actividades').value, 4);
      expect(stat(tester, 'Pendientes').value, 2);
      expect(stat(tester, 'En progreso').value, 1);
      expect(stat(tester, 'Completadas').value, 1);
      expect(stat(tester, 'Bloqueadas').value, 0);
      // There is no percentage and no progress bar anywhere on the panel
      expect(find.byType(LinearProgressIndicator), findsNothing);
      expect(find.textContaining('%'), findsNothing);
    });

    testWidgets('with no logbook the indicators are zero and the list says there is no logbook yet', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(stat(tester, 'Total de actividades').value, 0);
      expect(find.text('Todavía no hay bitácora de esta fecha. Se crea al planificar o registrar una actividad.'), findsOneWidget);
      expect(find.text('0 actividades en esta vista'), findsOneWidget);
    });

    testWidgets('each activity shows its title, description and current status as planned work', (tester) async {
      final logbook = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      expect(find.text('Preparar informe'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      expect(find.text('Pendiente'), findsWidgets); // the pill
      expect(find.text('Planificada'), findsOneWidget); // how it started, in words
      expect(find.textContaining(RegExp(r'\d\d:\d\d')), findsNothing); // no clock time is invented for it
      expect(find.text('1 actividad en esta vista'), findsOneWidget);
    });

    testWidgets('the Pendientes filter keeps only pending activities', (tester) async {
      final logbook = FakeLogbookRepository()
        ..seed(today, 'Pendiente uno')
        ..seed(today, 'Hecha', status: ActivityStatus.completed);
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      expect(find.text('Hecha'), findsOneWidget);
      final segmented = find.byWidgetPredicate((w) => w is SegmentedControl);
      await tester.tap(find.descendant(of: segmented, matching: find.text('Pendientes')));
      await tester.pumpAndSettle();
      expect(find.text('Hecha'), findsNothing);
      expect(find.text('Pendiente uno'), findsOneWidget);
      expect(find.text('1 actividad en esta vista'), findsOneWidget);
      await tester.tap(find.descendant(of: segmented, matching: find.text('Todas')));
      await tester.pumpAndSettle();
      expect(find.text('Hecha'), findsOneWidget);
    });

    testWidgets('the calendar shows the month, changes month and marks the selected day', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(find.text('Noviembre de 2026'), findsOneWidget);
      await tester.tap(find.byKey(const Key('month-next')));
      await tester.pumpAndSettle();
      expect(find.text('Diciembre de 2026'), findsOneWidget);
      await tester.tap(find.byKey(const Key('month-previous')));
      await tester.tap(find.byKey(const Key('month-previous')));
      await tester.pumpAndSettle();
      expect(find.text('Octubre de 2026'), findsOneWidget);
    });

    testWidgets('the main action opens the panel and the footer link goes to its page', (tester) async {
      await pumpApp(tester, auth: signedIn());
      await tester.tap(find.byKey(const Key('dashboard-new-activity')));
      await tester.pumpAndSettle();
      expect(find.text('Nueva actividad'), findsWidgets);
      expect(find.byKey(const Key('plan-title')), findsOneWidget);
      expect(find.text('Ver bitácora →'), findsOneWidget); // the dashboard is still behind the panel
      await tester.tap(find.byKey(const Key('plan-cancel')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('plan-title')), findsNothing);
      await tester.tap(find.text('Ver bitácora →'));
      await tester.pumpAndSettle();
      expect(find.text('Mi bitácora'), findsWidgets);
      expect(find.byKey(const Key('work-date')), findsOneWidget);
    });

    testWidgets('a loading failure offers to retry', (tester) async {
      final logbook = FakeLogbookRepository()..getError = const ApiError(code: ApiError.network, message: 'x');
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      expect(find.byKey(const Key('load-error')), findsOneWidget);
      logbook.getError = null;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('load-error')), findsNothing);
      expect(find.byKey(const Key('dashboard-empty')), findsOneWidget);
    });
  });

  group('logbook', () {
    testWidgets('with no logbook: consulting does not create it, and it can be opened', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'logbook');
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
      expect(logbook.days, isEmpty);
      expect(logbook.calls.where((c) => c.startsWith('open')), isEmpty);

      await tester.tap(find.byKey(const Key('open-logbook')));
      await tester.pumpAndSettle();
      expect(logbook.calls.where((c) => c.startsWith('open')), ['open 2026-11-06']);
      expect(logbook.calls.last, 'get 2026-11-06');
      expect(find.byKey(const Key('no-logbook')), findsNothing);
      expect(find.text('Abierta'), findsOneWidget);
      expect(find.text('Sin resumen'), findsOneWidget);
    });

    testWidgets('a persisted logbook shows its state and its three dates apart', (tester) async {
      final logbook = FakeLogbookRepository()..seed(today, 'Algo');
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'logbook');
      expect(find.text('Abierta'), findsOneWidget);
      expect(find.text('Jornada actual'), findsOneWidget);
      expect(find.text('Fecha laboral'), findsWidgets);
      expect(find.text('Registrada'), findsOneWidget);
      expect(find.text('Modificada'), findsOneWidget);
      expect(find.text('2026-11-06'), findsWidgets);
    });

    testWidgets('the date selector changes the consulted date', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      // From the calendar: past day -> logbook page of that date
      await tester.tap(find.byKey(const Key('cal-day-5')));
      await tester.pumpAndSettle();
      expect(find.text('05/11/2026'), findsOneWidget);
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
      await go(tester, 'dashboard');
      await tester.tap(find.byKey(const Key('cal-day-7')));
      await tester.pumpAndSettle();
      expect(find.text('07/11/2026'), findsOneWidget);
      await go(tester, 'dashboard');
      await tester.tap(find.byKey(const Key('cal-day-6')));
      await tester.pumpAndSettle();
      expect(find.text('06/11/2026'), findsOneWidget);
      expect(
        logbook.calls.where((c) => c.startsWith('get')).toSet(),
        {'get 2026-11-06', 'get 2026-11-05', 'get 2026-11-07'},
      );
    });

    testWidgets('a future date is labelled as such once its logbook exists', (tester) async {
      final logbook = FakeLogbookRepository()..seed(DateTime.utc(2026, 11, 7), 'Para mañana');
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await tester.tap(find.byKey(const Key('cal-day-7')));
      await tester.pumpAndSettle();
      expect(find.text('Jornada futura'), findsOneWidget);
      expect(find.text('Para mañana'), findsOneWidget);
    });

    testWidgets('the planning is not mistaken for a progress entry', (tester) async {
      final logbook = FakeLogbookRepository()..seed(today, 'Algo');
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'logbook');
      expect(find.text('La planificación es distinta de un avance de ejecución.'), findsOneWidget);
      expect(find.textContaining('Planificada'), findsOneWidget);
    });

    testWidgets('a loading failure on the logbook page offers to retry', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'logbook');
      logbook.getError = const ApiError(code: ApiError.network, message: 'x');
      await go(tester, 'dashboard');
      await tester.tap(find.byKey(const Key('cal-day-8')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('load-error')), findsOneWidget);
      logbook.getError = null;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
    });
  });

  group('planning', () {
    testWidgets('an empty title is rejected on screen without calling the server', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: '   ');
      expect(find.text('El título es obligatorio.'), findsOneWidget);
      expect(logbook.keys, isEmpty);
    });

    testWidgets('the initial status is pending, told as text, with no state selector and no progress', (tester) async {
      await pumpApp(tester, auth: signedIn());
      await go(tester, 'planning');
      expect(find.text('Estado inicial: Pendiente'), findsOneWidget);
      expect(find.text('Guardar una planificación no registra avances.'), findsOneWidget);
      expect(find.byKey(const Key('unplanned-status-completed')), findsNothing); // no state to pick
      expect(tester.widgetList<TextField>(find.byType(TextField)).where((f) => f.enabled == false), isEmpty); // nothing disabled to explain
      expect(find.textContaining('%'), findsNothing); // no percentages
    });

    testWidgets('creating an activity reloads from the server and shows it as planned, not as progress', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Preparar informe', description: 'Revisar cifras');

      expect(logbook.keys, hasLength(1));
      expect(RegExp(r'^[0-9a-f]{32}$').hasMatch(logbook.keys.single), isTrue);
      expect(logbook.calls.last, 'get 2026-11-06'); // after saving the screen consulted the server again
      // The panel closes, the person stays on Planificación, and the confirmation says what was saved
      expect(find.byKey(const Key('plan-submit')), findsNothing);
      expect(find.byKey(const Key('planning-new-activity')), findsOneWidget);
      expect(find.text('Actividad planificada.'), findsOneWidget);
      // Mi bitácora of that date shows what is persisted
      await go(tester, 'logbook');
      expect(find.text('Preparar informe'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      expect(find.text('Pendiente'), findsOneWidget);
      expect(find.textContaining('Planificada'), findsOneWidget);
      expect(find.byKey(const Key('no-logbook')), findsNothing); // the logbook was created implicitly
    });

    testWidgets('each new intention uses a different idempotency key', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Una');
      await tester.tap(find.byKey(const Key('planning-new-activity')));
      await tester.pumpAndSettle();
      await planFromScreen(tester, title: 'Otra');
      expect(logbook.keys.toSet(), hasLength(2));
      await go(tester, 'logbook');
      expect(find.text('Una'), findsOneWidget);
      expect(find.text('Otra'), findsOneWidget);
    });

    testWidgets('retrying after a failure reuses the SAME key and keeps the typed text', (tester) async {
      final logbook = FakeLogbookRepository()..createErrors.add(const ApiError(code: ApiError.network, message: 'x'));
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Preparar informe');
      expect(
        find.text('No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.'),
        findsOneWidget,
      );
      expect(logbook.days, isEmpty); // nothing persisted
      expect(tester.widget<TextField>(find.byKey(const Key('plan-title'))).controller!.text, 'Preparar informe');

      await submitPlanning(tester);
      expect(logbook.keys, hasLength(2));
      expect(logbook.keys[0], logbook.keys[1]);
      expect(logbook.days.values.expand((d) => d.activities), hasLength(1));
      expect(find.text('Actividad planificada.'), findsOneWidget);
    });

    testWidgets('a rejected date shows its own message', (tester) async {
      final logbook = FakeLogbookRepository()
        ..createErrors.add(const ApiError(code: 'FECHA_NO_CUBIERTA', message: 'x', status: 422));
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Algo');
      expect(find.text('Esa fecha no está cubierta por tu pertenencia a un equipo.'), findsOneWidget);
      expect(logbook.days, isEmpty);
    });

    testWidgets('planning is saved for the selected date only', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await tester.tap(find.byKey(const Key('cal-day-7'))); // selects 2026-11-07 and opens its logbook
      await tester.pumpAndSettle();
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Para mañana');
      expect(logbook.days.keys, ['2026-11-07']);
      await go(tester, 'dashboard');
      await tester.tap(find.byKey(const Key('cal-day-6')));
      await tester.pumpAndSettle();
      expect(find.text('Para mañana'), findsNothing);
      expect(find.byKey(const Key('no-logbook')), findsOneWidget);
    });

    testWidgets('cancel closes the panel, leaves Planificación with its button and saves nothing', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await tester.tap(find.byKey(const Key('plan-cancel')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('plan-submit')), findsNothing);
      expect(find.byKey(const Key('planning-new-activity')), findsOneWidget);
      expect(logbook.keys, isEmpty);
    });

    testWidgets('when the server stops recognizing the session the app returns to the login', (tester) async {
      final logbook = FakeLogbookRepository()
        ..createErrors.add(const ApiError(code: ApiError.notSignedIn, message: 'x', status: 401));
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Algo');
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(find.byKey(const Key('plan-submit')), findsNothing);
    });
  });

  group('responsive layout', () {
    double top(WidgetTester tester, String label) =>
        tester.getTopLeft(find.byWidgetPredicate((w) => w is StatCard && w.label == label)).dy;

    testWidgets('desktop: fixed sidebar, date chip and five indicators in one row', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(find.byKey(const Key('nav-dashboard')), findsOneWidget);
      expect(find.byKey(const Key('menu-toggle')), findsNothing);
      expect(find.byKey(const Key('top-date')), findsOneWidget);
      expect(top(tester, 'Total de actividades'), top(tester, 'Completadas'));
      expect(tester.getSize(find.byKey(const Key('nav-dashboard'))).width, closeTo(232 - 24, 1)); // sidebar 232 px, 12 px of padding each side
    });

    testWidgets('tablet: narrower sidebar and three columns of indicators', (tester) async {
      await pumpApp(tester, auth: signedIn(), size: tablet);
      expect(find.byKey(const Key('nav-dashboard')), findsOneWidget);
      expect(find.byKey(const Key('menu-toggle')), findsNothing);
      expect(tester.getSize(find.byKey(const Key('nav-dashboard'))).width, closeTo(208 - 24, 1)); // sidebar 208 px
      expect(top(tester, 'Total de actividades'), top(tester, 'En progreso'));
      expect(top(tester, 'Bloqueadas'), greaterThan(top(tester, 'En progreso')));
      // The calendar goes below the activities (single column)
      expect(tester.getTopLeft(find.text('Calendario')).dy, greaterThan(tester.getTopLeft(find.text('Actividades de la jornada')).dy));
    });

    testWidgets('mobile: the sidebar is a drawer opened from the top bar', (tester) async {
      await pumpApp(tester, auth: signedIn(), size: mobile);
      expect(find.byKey(const Key('nav-dashboard')), findsNothing);
      expect(find.byKey(const Key('top-date')), findsNothing);
      expect(find.byKey(const Key('menu-toggle')), findsOneWidget);

      await tester.tap(find.byKey(const Key('menu-toggle')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('nav-dashboard')), findsOneWidget);
      expect(find.byKey(const Key('nav-planning')), findsOneWidget);

      await tester.tap(find.byKey(const Key('nav-planning')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('nav-dashboard')), findsNothing); // the drawer closed
      expect(find.byKey(const Key('plan-title')), findsOneWidget);
    });

    testWidgets('mobile: logout from the drawer', (tester) async {
      final auth = signedIn();
      await pumpApp(tester, auth: auth, size: mobile);
      await tester.tap(find.byKey(const Key('menu-toggle')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('logout')));
      await tester.pumpAndSettle();
      expect(auth.logoutCalls, 1);
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });

    testWidgets('mobile: every page fits without overflowing', (tester) async {
      final logbook = FakeLogbookRepository()..seed(today, 'Una actividad con un título bastante largo para comprobar el ajuste', description: 'Una descripción también larga para ver cómo se parte en varias líneas dentro de la tarjeta');
      await pumpApp(tester, auth: signedIn(), logbook: logbook, size: mobile);
      await tester.tap(find.byKey(const Key('menu-toggle')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('nav-logbook')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('menu-toggle')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('nav-planning')));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });

    testWidgets('there is no notifications button: the product has no notifications, so none is offered', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(find.byTooltip('Notificaciones no disponibles'), findsNothing);
      expect(find.byIcon(Icons.notifications_none_outlined), findsNothing);
    });
  });
}
