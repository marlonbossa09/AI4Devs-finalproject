import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/errors/error_messages.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/core/theme/app_theme.dart';
import 'package:smartwork/core/utils/wait.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/domain/repository/auth_repository.dart';
import 'package:smartwork/features/auth/presentation/pages/login_page.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// M1-T7: the login screen when the server limits the attempts (HTTP 429 with `Retry-After`).

ApiError tooMany(int? seconds) => ApiError(
  code: ApiError.tooManyRequests,
  message: 'x',
  status: 429,
  details: seconds == null
      ? const []
      : [
          {'espera_segundos': seconds},
        ],
  retryAfterSeconds: seconds,
);

const wrong = ApiError(code: 'CREDENCIALES_INVALIDAS', message: 'x', status: 401);

/// Answers each login with the next scripted outcome (an error to throw, or null to succeed).
class ScriptedAuth implements AuthRepository {
  ScriptedAuth(this.outcomes);

  final List<ApiError?> outcomes;
  final List<String> attempts = [];

  @override
  Future<Session?> getSession() async => null;

  @override
  Future<Session> login({required String user, required String password}) async {
    attempts.add(user);
    final next = outcomes.isEmpty ? null : outcomes.removeAt(0);
    if (next != null) throw next;
    return sampleSession();
  }

  @override
  Future<void> logout() async {}
}

class Clock {
  DateTime now = DateTime.utc(2026, 11, 17, 9);
  DateTime call() => now;
}

Future<Clock> pumpLogin(WidgetTester tester, ScriptedAuth auth, {Size size = const Size(1400, 1000)}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final clock = Clock();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(auth)],
      child: MaterialApp(
        theme: AppTheme.build(webFonts: false),
        home: LoginPage(clock: clock.call),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return clock;
}

Future<void> submit(WidgetTester tester, {String user = 'ana', String password = 'una-contraseña-larga'}) async {
  await tester.enterText(find.byKey(const Key('login-id')), user);
  await tester.enterText(find.byKey(const Key('login-password')), password);
  await tester.tap(find.byKey(const Key('login-submit')));
  await tester.pump();
  await tester.pump();
}

/// Advances the fake timers and the injected clock together, one second at a time.
Future<void> elapse(WidgetTester tester, Clock clock, int seconds) async {
  for (var i = 0; i < seconds; i++) {
    clock.now = clock.now.add(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
  }
}

bool submitEnabled(WidgetTester tester) => tester
    .widget<FilledButton>(find.descendant(of: find.byKey(const Key('login-submit')), matching: find.byType(FilledButton)))
    .onPressed !=
    null;

String message(WidgetTester tester) => tester.widget<Text>(find.byKey(const Key('login-error'))).data!;

void main() {
  setUpAll(loadTestFonts);

  group('wait helpers', () {
    test('formats the countdown below and above an hour', () {
      expect(formatWait(0), '0:00');
      expect(formatWait(29), '0:29');
      expect(formatWait(30), '0:30');
      expect(formatWait(60), '1:00');
      expect(formatWait(1920), '32:00');
      expect(formatWait(3599), '59:59');
      expect(formatWait(3600), '1:00:00');
      expect(formatWait(-5), '0:00');
    });

    test('remaining seconds are rounded up and never negative', () {
      final start = DateTime.utc(2026, 11, 17, 9);
      final wait = Wait.from(start, 30);
      expect(wait.remainingSeconds(start), 30);
      expect(wait.remainingSeconds(start.add(const Duration(milliseconds: 1500))), 29);
      expect(wait.remainingSeconds(start.add(const Duration(seconds: 30))), 0);
      expect(wait.remainingSeconds(start.add(const Duration(seconds: 99))), 0);
    });
  });

  group('Retry-After reading', () {
    ApiError parse(Map<String, dynamic> body, {Map<String, List<String>> headers = const {}, int status = 429}) {
      final request = RequestOptions(path: '/sesion');
      return errorFromDio(
        DioException(
          requestOptions: request,
          response: Response(requestOptions: request, statusCode: status, data: body, headers: Headers.fromMap(headers)),
        ),
      );
    }

    Map<String, dynamic> body({List<Map<String, dynamic>> details = const []}) => {
      'codigo': 'DEMASIADAS_SOLICITUDES',
      'mensaje': 'x',
      'detalles': details,
    };

    test('reads the header in seconds', () {
      final error = parse(body(), headers: {'retry-after': ['45']});
      expect(error.isTooManyRequests, isTrue);
      expect(error.retryAfterSeconds, 45);
      expect(error.status, 429);
    });

    test('the header wins over the body, and the body is the fallback', () {
      final both = parse(
        body(details: [{'espera_segundos': 99}]),
        headers: {'retry-after': ['45']},
      );
      expect(both.retryAfterSeconds, 45);
      final onlyBody = parse(body(details: [{'espera_segundos': 99}]));
      expect(onlyBody.retryAfterSeconds, 99);
    });

    test('ignores anything that is not a positive number of seconds', () {
      for (final bad in ['abc', '0', '-3', '', '1.5', 'Wed, 21 Oct 2026 07:28:00 GMT', '999999999']) {
        expect(parse(body(), headers: {'retry-after': [bad]}).retryAfterSeconds, isNull, reason: bad);
      }
    });

    test('other errors carry no wait', () {
      expect(
        parse({'codigo': 'CREDENCIALES_INVALIDAS', 'mensaje': 'x', 'detalles': []}, status: 401).retryAfterSeconds,
        isNull,
      );
    });

    test('the message is fixed text with no data of the account', () {
      final text = errorMessage(tooMany(30));
      expect(text, contains('Demasiados intentos'));
      expect(text, isNot(contains('30')));
      expect(text, isNot(contains('existe')));
      expect(text, isNot(contains('quedan')));
    });
  });

  group('login screen with a wait', () {
    testWidgets('a 429 shows the fixed message with the countdown and disables the button', (tester) async {
      final auth = ScriptedAuth([tooMany(30)]);
      await pumpLogin(tester, auth);
      await submit(tester);
      expect(message(tester), 'Demasiados intentos. Vuelve a intentarlo en 0:30.');
      expect(submitEnabled(tester), isFalse);
      expect(tester.widget<TextField>(find.byKey(const Key('login-password'))).controller!.text, isEmpty);
      // Not a word about the account or the remaining attempts
      expect(find.textContaining('queda'), findsNothing);
      expect(find.textContaining('existe'), findsNothing);
    });

    testWidgets('counts down from the time the server communicated and enables the button at zero', (tester) async {
      final auth = ScriptedAuth([tooMany(3)]);
      final clock = await pumpLogin(tester, auth);
      await submit(tester);
      expect(message(tester), endsWith('0:03.'));
      await elapse(tester, clock, 1);
      expect(message(tester), endsWith('0:02.'));
      await elapse(tester, clock, 1);
      expect(message(tester), endsWith('0:01.'));
      expect(submitEnabled(tester), isFalse);
      await elapse(tester, clock, 1);
      expect(find.byKey(const Key('login-error')), findsNothing);
      expect(submitEnabled(tester), isTrue);
    });

    testWidgets('no request is sent while the wait lasts, and one is sent after it', (tester) async {
      final auth = ScriptedAuth([tooMany(2), null]);
      final clock = await pumpLogin(tester, auth);
      await submit(tester);
      expect(auth.attempts, hasLength(1));
      await tester.tap(find.byKey(const Key('login-submit')), warnIfMissed: false);
      await tester.pump();
      // The person types the password again during the wait and presses Enter: it goes through the same guard as the button
      await tester.enterText(find.byKey(const Key('login-password')), 'una-contraseña-larga');
      tester.widget<TextField>(find.byKey(const Key('login-password'))).onSubmitted!('una-contraseña-larga');
      await tester.pump();
      expect(auth.attempts, hasLength(1));
      await elapse(tester, clock, 2);
      expect(submitEnabled(tester), isTrue);
      await submit(tester);
      expect(auth.attempts, hasLength(2));
    });

    testWidgets('a new 429 while the server still holds the restriction starts a new countdown', (tester) async {
      final auth = ScriptedAuth([tooMany(2), tooMany(60)]);
      final clock = await pumpLogin(tester, auth);
      await submit(tester);
      await elapse(tester, clock, 2);
      expect(submitEnabled(tester), isTrue);
      await submit(tester);
      expect(message(tester), 'Demasiados intentos. Vuelve a intentarlo en 1:00.');
      expect(submitEnabled(tester), isFalse);
      await elapse(tester, clock, 10);
      expect(message(tester), endsWith('0:50.'));
    });

    testWidgets('the countdown follows the clock, not the number of ticks (throttled tabs)', (tester) async {
      final auth = ScriptedAuth([tooMany(120)]);
      final clock = await pumpLogin(tester, auth);
      await submit(tester);
      clock.now = clock.now.add(const Duration(seconds: 100)); // the browser paused the timer for 100 s
      await tester.pump(const Duration(seconds: 1));
      expect(message(tester), endsWith('0:20.'));
    });

    testWidgets('a 429 without a valid wait shows the generic message and does not lock the form', (tester) async {
      final auth = ScriptedAuth([tooMany(null)]);
      await pumpLogin(tester, auth);
      await submit(tester);
      expect(message(tester), errorMessage(tooMany(null)));
      expect(submitEnabled(tester), isTrue);
    });

    testWidgets('a Retry-After on any other error does not start a wait', (tester) async {
      final auth = ScriptedAuth([
        const ApiError(code: 'CREDENCIALES_INVALIDAS', message: 'x', status: 401, retryAfterSeconds: 30),
      ]);
      await pumpLogin(tester, auth);
      await submit(tester);
      expect(message(tester), 'El usuario o la contraseña no son correctos.');
      expect(submitEnabled(tester), isTrue);
    });

    testWidgets('a wrong password shows the usual message and never starts a wait', (tester) async {
      final auth = ScriptedAuth([wrong]);
      await pumpLogin(tester, auth);
      await submit(tester);
      expect(message(tester), 'El usuario o la contraseña no son correctos.');
      expect(submitEnabled(tester), isTrue);
    });

    testWidgets('the countdown is plain text and the fixed message is announced once (not every second)', (tester) async {
      final auth = ScriptedAuth([tooMany(30)]);
      final clock = await pumpLogin(tester, auth);
      final handle = tester.ensureSemantics();
      await submit(tester);
      const fixed = 'Demasiados intentos. Espera un momento antes de volver a intentarlo.';
      final countdown = tester.getSemantics(find.byKey(const Key('login-error')));
      final live = tester.getSemantics(find.bySemanticsLabel(fixed));
      expect(countdown.label, contains('0:30'));
      expect(countdown.flagsCollection.isLiveRegion, isFalse); // changing every second, it must not be a live region
      expect(live.flagsCollection.isLiveRegion, isTrue); // announced once, with text that never changes
      await elapse(tester, clock, 5);
      expect(tester.getSemantics(find.byKey(const Key('login-error'))).label, contains('0:25'));
      expect(tester.getSemantics(find.bySemanticsLabel(fixed)).label, fixed);
      handle.dispose();
    });

    for (final (name, size) in [('mobile', const Size(400, 900)), ('tablet', const Size(900, 1000))]) {
      testWidgets('works on $name without overflow', (tester) async {
        final auth = ScriptedAuth([tooMany(1920)]);
        await pumpLogin(tester, auth, size: size);
        await submit(tester);
        expect(message(tester), endsWith('32:00.'));
        expect(tester.takeException(), isNull);
        expect(submitEnabled(tester), isFalse);
      });
    }

    testWidgets('leaving the screen during a wait cancels the timer', (tester) async {
      final auth = ScriptedAuth([tooMany(30)]);
      await pumpLogin(tester, auth);
      await submit(tester);
      await tester.pumpWidget(const SizedBox());
      await tester.pump(const Duration(seconds: 60));
      expect(tester.takeException(), isNull);
    });
  });
}
