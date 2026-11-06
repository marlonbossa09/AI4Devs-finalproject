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
      expect(find.text('Buen día, Carlos'), findsOneWidget);
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
      expect(stat(tester, 'Actividades registradas').value, 4);
      expect(stat(tester, 'Pendientes').value, 2);
      expect(stat(tester, 'En progreso').value, 1);
      expect(stat(tester, 'Completadas').value, 1);
      expect(textOf(tester, const Key('completion')), '1 de 4');
      expect(tester.widget<LinearProgressIndicator>(find.byKey(const Key('progress-bar'))).value, 0.25);
    });

    testWidgets('with no logbook the indicators are zero and the list is empty', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(stat(tester, 'Actividades registradas').value, 0);
      expect(find.text('No hay actividades para esta selección.'), findsOneWidget);
      expect(find.text('0 actividades en esta vista'), findsOneWidget);
      expect(textOf(tester, const Key('completion')), '0 de 0');
    });

    testWidgets('each activity shows its title, description and current status as planned work', (tester) async {
      final logbook = FakeLogbookRepository()..seed(today, 'Preparar informe', description: 'Revisar cifras');
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      expect(find.text('Preparar informe'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      expect(find.text('Pendiente'), findsWidgets); // the pill (and the indicator label)
      expect(find.textContaining('Planificada'), findsOneWidget);
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

    testWidgets('the main action and the footer link go to their pages', (tester) async {
      await pumpApp(tester, auth: signedIn());
      await tester.tap(find.byKey(const Key('dashboard-new-planning')));
      await tester.pumpAndSettle();
      expect(find.text('Nueva planificación'), findsWidgets);
      expect(find.byKey(const Key('plan-title')), findsOneWidget);
      await go(tester, 'dashboard');
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
      expect(find.text('No hay actividades para esta selección.'), findsOneWidget);
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
      await tester.tap(find.byKey(const Key('cal-day-6')).evaluate().isEmpty
          ? find.byKey(const Key('logbook-new-planning'))
          : find.byKey(const Key('cal-day-6')));
      await tester.pumpAndSettle();
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

    testWidgets('the initial status is pending and cannot be edited', (tester) async {
      await pumpApp(tester, auth: signedIn());
      await go(tester, 'planning');
      expect(find.text('Una planificación nueva inicia como pendiente.'), findsOneWidget);
      final fields = tester.widgetList<TextField>(find.byType(TextField)).where((f) => f.enabled == false);
      expect(fields, hasLength(1));
    });

    testWidgets('creating an activity reloads from the server and shows it as planned, not as progress', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Preparar informe', description: 'Revisar cifras');

      expect(logbook.keys, hasLength(1));
      expect(RegExp(r'^[0-9a-f]{32}$').hasMatch(logbook.keys.single), isTrue);
      expect(logbook.calls.last, 'get 2026-11-06'); // after saving the screen consulted the server again
      // It lands on the logbook of that date, which shows what is persisted
      expect(find.text('Preparar informe'), findsOneWidget);
      expect(find.text('Revisar cifras'), findsOneWidget);
      expect(find.text('Pendiente'), findsOneWidget);
      expect(find.textContaining('Planificada'), findsOneWidget);
      expect(find.byKey(const Key('no-logbook')), findsNothing); // the logbook was created implicitly
      expect(find.text('Actividad planificada.'), findsOneWidget);
    });

    testWidgets('each new intention uses a different idempotency key', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Una');
      await go(tester, 'planning');
      await planFromScreen(tester, title: 'Otra');
      expect(logbook.keys.toSet(), hasLength(2));
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
      expect(find.text('Preparar informe'), findsOneWidget);
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

    testWidgets('cancel goes back to the dashboard without saving', (tester) async {
      final logbook = FakeLogbookRepository();
      await pumpApp(tester, auth: signedIn(), logbook: logbook);
      await go(tester, 'planning');
      await tester.tap(find.byKey(const Key('plan-cancel')));
      await tester.pumpAndSettle();
      expect(find.text('Buen día, Carlos'), findsOneWidget);
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

    testWidgets('desktop: fixed sidebar, date chip and four indicators in one row', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(find.byKey(const Key('nav-dashboard')), findsOneWidget);
      expect(find.byKey(const Key('menu-toggle')), findsNothing);
      expect(find.byKey(const Key('top-date')), findsOneWidget);
      expect(top(tester, 'Actividades registradas'), top(tester, 'Completadas'));
      expect(tester.getSize(find.byKey(const Key('nav-dashboard'))).width, closeTo(246 - 32, 1));
    });

    testWidgets('tablet: narrower sidebar and two columns of indicators', (tester) async {
      await pumpApp(tester, auth: signedIn(), size: tablet);
      expect(find.byKey(const Key('nav-dashboard')), findsOneWidget);
      expect(find.byKey(const Key('menu-toggle')), findsNothing);
      expect(tester.getSize(find.byKey(const Key('nav-dashboard'))).width, closeTo(215 - 32, 1));
      expect(top(tester, 'Actividades registradas'), top(tester, 'Pendientes'));
      expect(top(tester, 'En progreso'), greaterThan(top(tester, 'Pendientes')));
      // The calendar goes below the activities (single column)
      expect(tester.getTopLeft(find.text('Calendario')).dy, greaterThan(tester.getTopLeft(find.text('Actividades de mi jornada')).dy));
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

    testWidgets('the notifications button is disabled and says so', (tester) async {
      await pumpApp(tester, auth: signedIn());
      expect(find.byTooltip('Notificaciones no disponibles'), findsOneWidget);
    });
  });
}
