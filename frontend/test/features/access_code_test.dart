import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/network/api_client.dart';
import 'package:smartwork/core/theme/app_theme.dart';
import 'package:smartwork/features/auth/data/remote/auth_remote_data_source.dart';
import 'package:smartwork/features/auth/data/repository/access_code_repository_impl.dart';
import 'package:smartwork/features/auth/domain/repository/access_code_repository.dart';
import 'package:smartwork/features/auth/presentation/pages/login_page.dart';
import 'package:smartwork/features/auth/presentation/providers/access_code_repository.dart';
import 'package:smartwork/features/auth/presentation/providers/auth_repository.dart';

import '../helpers/fakes.dart';
import '../helpers/fonts.dart';

/// M1-T8.5: the first access (M1-03b) and recovery (M1-09b) screens, reached from the login.

class Call {
  Call(this.purpose, this.identifier, this.code, this.newPassword);
  final AccessCodePurpose purpose;
  final String identifier;
  final String code;
  final String newPassword;
}

/// Records every redemption and answers with the next scripted outcome (an error to throw, or null to succeed).
class FakeAccessCodes implements AccessCodeRepository {
  FakeAccessCodes([List<ApiError?> outcomes = const []]) : outcomes = [...outcomes];

  final List<ApiError?> outcomes;
  final List<Call> calls = [];
  Completer<void>? gate;

  @override
  Future<void> redeem(
    AccessCodePurpose purpose, {
    required String identifier,
    required String code,
    required String newPassword,
  }) async {
    calls.add(Call(purpose, identifier, code, newPassword));
    if (gate != null) await gate!.future;
    final next = outcomes.isEmpty ? null : outcomes.removeAt(0);
    if (next != null) throw next;
  }
}

const invalidCode = ApiError(code: 'CODIGO_NO_VALIDO', message: 'x', status: 400);
ApiError weak(String reason) => ApiError(
  code: 'CONTRASENA_NO_VALIDA',
  message: 'x',
  status: 422,
  details: [
    {'campo': 'contrasena_nueva', 'motivo': reason},
  ],
);
ApiError tooMany(int seconds) => ApiError(
  code: ApiError.tooManyRequests,
  message: 'x',
  status: 429,
  details: [
    {'espera_segundos': seconds},
  ],
  retryAfterSeconds: seconds,
);

class Clock {
  DateTime now = DateTime.utc(2026, 11, 17, 9);
  DateTime call() => now;
}

Future<Clock> pumpLogin(WidgetTester tester, FakeAccessCodes codes, FakeAuthRepository auth, {Size size = const Size(1400, 1000)}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final clock = Clock();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [accessCodeRepositoryProvider.overrideWithValue(codes), authRepositoryProvider.overrideWithValue(auth)],
      child: MaterialApp(theme: AppTheme.build(webFonts: false), home: LoginPage(clock: clock.call)),
    ),
  );
  await tester.pumpAndSettle();
  return clock;
}

Future<void> open(WidgetTester tester, String link) async {
  await tester.ensureVisible(find.byKey(Key(link)));
  await tester.tap(find.byKey(Key(link)));
  await tester.pumpAndSettle();
}

Future<void> fill(
  WidgetTester tester, {
  String user = ' ana ',
  String code = 'ABCDE-FGHJK-MNPQR-STVWX-YZ0123',
  String password = 'una-contraseña-larga-1',
  String? confirmation,
}) async {
  await tester.enterText(find.byKey(const Key('access-identifier')), user);
  await tester.enterText(find.byKey(const Key('access-code')), code);
  await tester.enterText(find.byKey(const Key('access-password')), password);
  await tester.enterText(find.byKey(const Key('access-confirmation')), confirmation ?? password);
}

Future<void> submit(WidgetTester tester) async {
  await tester.ensureVisible(find.byKey(const Key('access-submit')));
  await tester.tap(find.byKey(const Key('access-submit')));
  await tester.pump();
  await tester.pump();
}

String errorText(WidgetTester tester) => tester.widget<Text>(find.byKey(const Key('access-error'))).data!;

bool submitEnabled(WidgetTester tester) => tester
    .widget<FilledButton>(find.descendant(of: find.byKey(const Key('access-submit')), matching: find.byType(FilledButton)))
    .onPressed !=
    null;

String fieldText(WidgetTester tester, String key) => tester.widget<TextField>(find.byKey(Key(key))).controller!.text;

bool obscured(WidgetTester tester, String key) => tester.widget<TextField>(find.byKey(Key(key))).obscureText;

void main() {
  setUpAll(loadTestFonts);

  group('first access', () {
    testWidgets('redeems the code, returns to the login with a notice and creates no session', (tester) async {
      final codes = FakeAccessCodes();
      final auth = FakeAuthRepository();
      await pumpLogin(tester, codes, auth);
      await open(tester, 'login-first-access');
      expect(find.text('Establece tu contraseña'), findsOneWidget);
      await fill(tester);
      await submit(tester);
      await tester.pumpAndSettle();
      expect(codes.calls, hasLength(1));
      final call = codes.calls.single;
      expect(call.purpose, AccessCodePurpose.firstAccess);
      expect(call.identifier, 'ana'); // trimmed
      expect(call.code, 'ABCDE-FGHJK-MNPQR-STVWX-YZ0123');
      expect(call.newPassword, 'una-contraseña-larga-1');
      // Back on the login, with the notice; nobody was signed in and the login was never called.
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(find.byKey(const Key('login-notice')), findsOneWidget);
      expect(find.text('Tu contraseña quedó establecida. Ya puedes iniciar sesión.'), findsOneWidget);
      expect(auth.loginAttempts, isEmpty);
      expect(find.byKey(const Key('access-code')), findsNothing);
    });
  });

  group('recovery', () {
    testWidgets('changes the password, returns to the login and says the sessions were closed', (tester) async {
      final codes = FakeAccessCodes();
      final auth = FakeAuthRepository();
      await pumpLogin(tester, codes, auth);
      await open(tester, 'login-recovery');
      expect(find.text('Elige una contraseña nueva'), findsOneWidget);
      expect(find.textContaining('no se envía por correo ni por mensaje'), findsOneWidget); // recovery is administrative
      await fill(tester);
      await submit(tester);
      await tester.pumpAndSettle();
      expect(codes.calls.single.purpose, AccessCodePurpose.recovery);
      expect(find.text('Tu contraseña cambió y se cerraron tus sesiones anteriores. Ya puedes iniciar sesión.'), findsOneWidget);
      expect(auth.loginAttempts, isEmpty);
    });

    testWidgets('going back without redeeming shows no notice and calls nothing', (tester) async {
      final codes = FakeAccessCodes();
      await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-recovery');
      await tester.tap(find.byKey(const Key('access-back')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
      expect(find.byKey(const Key('login-notice')), findsNothing);
      expect(codes.calls, isEmpty);
    });
  });

  group('form', () {
    testWidgets('basic validations stop the request before it is sent', (tester) async {
      final codes = FakeAccessCodes();
      await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-first-access');
      await submit(tester);
      expect(find.text('Escribe tu usuario.'), findsOneWidget);
      expect(find.text('Escribe el código que te entregaron.'), findsOneWidget);
      expect(find.text('La contraseña debe tener al menos 10 caracteres.'), findsOneWidget);
      await fill(tester, password: 'corta');
      await submit(tester);
      expect(find.text('La contraseña debe tener al menos 10 caracteres.'), findsOneWidget);
      await fill(tester, password: 'una-contraseña-larga-1', confirmation: 'otra-contraseña-larga-2');
      await submit(tester);
      expect(find.text('Las contraseñas no coinciden.'), findsOneWidget);
      expect(codes.calls, isEmpty);
    });

    testWidgets('the show/hide button toggles both password fields and starts hidden', (tester) async {
      await pumpLogin(tester, FakeAccessCodes(), FakeAuthRepository());
      await open(tester, 'login-first-access');
      expect(obscured(tester, 'access-password'), isTrue);
      expect(obscured(tester, 'access-confirmation'), isTrue);
      await tester.tap(find.byKey(const Key('access-toggle-passwords')));
      await tester.pump();
      expect(obscured(tester, 'access-password'), isFalse);
      expect(obscured(tester, 'access-confirmation'), isFalse);
      expect(find.byTooltip('Ocultar las contraseñas'), findsOneWidget);
      await tester.tap(find.byKey(const Key('access-toggle-passwords')));
      await tester.pump();
      expect(obscured(tester, 'access-password'), isTrue);
    });

    for (final (name, size) in [('mobile', const Size(400, 900)), ('tablet', const Size(900, 1000)), ('desktop', const Size(1400, 1000))]) {
      testWidgets('lays out on $name without overflow', (tester) async {
        await pumpLogin(tester, FakeAccessCodes([invalidCode]), FakeAuthRepository(), size: size);
        await open(tester, 'login-recovery');
        await fill(tester);
        await submit(tester);
        expect(tester.takeException(), isNull);
        expect(find.byKey(const Key('access-submit')), findsOneWidget);
      });
    }
  });

  group('errors', () {
    testWidgets('every invalid code gets the same message, the passwords are cleared and the code is kept', (tester) async {
      final codes = FakeAccessCodes([invalidCode]);
      await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-first-access');
      await fill(tester);
      await submit(tester);
      expect(errorText(tester), startsWith('El código no es válido o ya no se puede usar'));
      expect(fieldText(tester, 'access-password'), isEmpty);
      expect(fieldText(tester, 'access-confirmation'), isEmpty);
      expect(fieldText(tester, 'access-code'), 'ABCDE-FGHJK-MNPQR-STVWX-YZ0123'); // so a typo can be fixed
      expect(submitEnabled(tester), isTrue);
      expect(find.text('Establece tu contraseña'), findsOneWidget); // still here: nothing was redeemed
      // Not a word about whether the user exists, the code expired or was used.
      expect(find.textContaining('caduc'), findsNothing);
      expect(find.textContaining('existe'), findsNothing);
    });

    testWidgets('a password the server rejects is explained and does not leave the screen', (tester) async {
      final codes = FakeAccessCodes([weak('comprometida')]);
      await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-recovery');
      await fill(tester);
      await submit(tester);
      expect(errorText(tester), 'Esa contraseña no es segura. Elige otra.');
      expect(find.text('Elige una contraseña nueva'), findsOneWidget);
    });

    testWidgets('a network failure shows the generic connection message', (tester) async {
      final codes = FakeAccessCodes([const ApiError(code: ApiError.network, message: 'x')]);
      await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-first-access');
      await fill(tester);
      await submit(tester);
      expect(errorText(tester), startsWith('No se pudo conectar con el servidor'));
    });
  });

  group('429 wait', () {
    testWidgets('shows the countdown the server communicated, disables the button and enables it again at zero', (tester) async {
      final codes = FakeAccessCodes([tooMany(3)]);
      final clock = await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-first-access');
      await fill(tester);
      await submit(tester);
      expect(errorText(tester), 'Demasiados intentos. Vuelve a intentarlo en 0:03.');
      expect(submitEnabled(tester), isFalse);
      expect(fieldText(tester, 'access-password'), isEmpty);
      // While it lasts, neither the button nor Enter send anything.
      await fill(tester);
      tester.widget<TextField>(find.byKey(const Key('access-confirmation'))).onSubmitted!('una-contraseña-larga-1');
      await tester.pump();
      expect(codes.calls, hasLength(1));
      for (var i = 0; i < 3; i++) {
        clock.now = clock.now.add(const Duration(seconds: 1));
        await tester.pump(const Duration(seconds: 1));
      }
      expect(find.byKey(const Key('access-error')), findsNothing);
      expect(submitEnabled(tester), isTrue);
      await submit(tester);
      await tester.pumpAndSettle();
      expect(codes.calls, hasLength(2));
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });

    testWidgets('a new 429 while the server still holds the restriction starts a new countdown', (tester) async {
      final codes = FakeAccessCodes([tooMany(2), tooMany(60)]);
      final clock = await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-recovery');
      await fill(tester);
      await submit(tester);
      for (var i = 0; i < 2; i++) {
        clock.now = clock.now.add(const Duration(seconds: 1));
        await tester.pump(const Duration(seconds: 1));
      }
      await fill(tester);
      await submit(tester);
      expect(errorText(tester), 'Demasiados intentos. Vuelve a intentarlo en 1:00.');
      expect(submitEnabled(tester), isFalse);
    });
  });

  group('duplicate requests', () {
    testWidgets('a second tap or Enter while the request is in flight sends nothing and the screen shows it is loading', (tester) async {
      final codes = FakeAccessCodes()..gate = Completer<void>();
      await pumpLogin(tester, codes, FakeAuthRepository());
      await open(tester, 'login-first-access');
      await fill(tester);
      await submit(tester);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      await tester.tap(find.byKey(const Key('access-submit')), warnIfMissed: false);
      await tester.pump();
      expect(codes.calls, hasLength(1));
      codes.gate!.complete();
      await tester.pumpAndSettle();
      expect(codes.calls, hasLength(1));
      expect(find.byKey(const Key('login-notice')), findsOneWidget);
    });
  });

  group('data layer', () {
    ApiClient clientFor(FakeAdapter adapter) => ApiClient(dio: Dio()..httpClientAdapter = adapter);

    test('posts to the contract routes with the exact body and never sends a CSRF token or reads a session', () async {
      final adapter = FakeAdapter((_) => ResponseBody.fromString('', 204));
      final client = clientFor(adapter);
      final repository = AccessCodeRepositoryImpl(AuthRemoteDataSource(client));
      await repository.redeem(AccessCodePurpose.firstAccess, identifier: 'ana', code: 'C-1', newPassword: 'p-1');
      await repository.redeem(AccessCodePurpose.recovery, identifier: 'ana', code: 'C-2', newPassword: 'p-2');
      expect(adapter.requests.map((r) => r.path), ['/api/v1/acceso/primer-acceso', '/api/v1/acceso/recuperacion']);
      expect(adapter.requests.every((r) => r.method == 'POST'), isTrue);
      expect(adapter.requests[0].data, {'identificador_acceso': 'ana', 'codigo': 'C-1', 'contrasena_nueva': 'p-1'});
      expect(adapter.requests[1].data, {'identificador_acceso': 'ana', 'codigo': 'C-2', 'contrasena_nueva': 'p-2'});
      expect(adapter.requests.every((r) => !r.headers.containsKey('X-CSRF-Token')), isTrue);
      expect(client.csrf, isNull); // redeeming leaves no session in the client
    });

    test('maps the uniform errors of the contract to ApiError, with the wait of a 429', () async {
      final bodies = <ResponseBody>[
        jsonBody({'codigo': 'CODIGO_NO_VALIDO', 'mensaje': 'x', 'detalles': []}, status: 400),
        ResponseBody.fromString(
          '{"codigo":"DEMASIADAS_SOLICITUDES","mensaje":"x","detalles":[{"espera_segundos":30}]}',
          429,
          headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
            'retry-after': ['30'],
          },
        ),
      ];
      final repository = AccessCodeRepositoryImpl(AuthRemoteDataSource(clientFor(FakeAdapter((_) => bodies.removeAt(0)))));
      await expectLater(
        repository.redeem(AccessCodePurpose.recovery, identifier: 'a', code: 'c', newPassword: 'p'),
        throwsA(isA<ApiError>().having((e) => e.code, 'code', 'CODIGO_NO_VALIDO')),
      );
      await expectLater(
        repository.redeem(AccessCodePurpose.firstAccess, identifier: 'a', code: 'c', newPassword: 'p'),
        throwsA(isA<ApiError>().having((e) => e.retryAfterSeconds, 'wait', 30)),
      );
    });
  });
}
