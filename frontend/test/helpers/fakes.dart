import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/domain/repository/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/repository/logbook_repository.dart';

/// Server "today" used by the tests.
final DateTime today = DateTime.utc(2026, 11, 6);

Session sampleSession({Role role = Role.collaborator}) => Session(
  user: const User(id: 'p1', name: 'Carlos Colaborador (demo)'),
  role: role,
  csrf: 'csrf-1',
  today: today,
);

/// Dio adapter that answers from a function and records the requests.
class FakeAdapter implements HttpClientAdapter {
  FakeAdapter(this.handler);

  final ResponseBody Function(RequestOptions options) handler;
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonBody(Object body, {int status = 200}) => ResponseBody.fromString(
  jsonEncode(body),
  status,
  headers: {
    Headers.contentTypeHeader: [Headers.jsonContentType],
  },
);

class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository({this.session, this.loginError});

  Session? session;
  ApiError? loginError;
  int logoutCalls = 0;
  final List<String> loginAttempts = [];

  @override
  Future<Session?> getSession() async => session;

  @override
  Future<Session> login({required String user, required String password}) async {
    loginAttempts.add(user);
    final error = loginError;
    if (error != null) throw error;
    return session = sampleSession();
  }

  @override
  Future<void> logout() async {
    logoutCalls++;
    session = null;
  }
}

/// In-memory "server": what it holds is what the screen must show after reloading.
class FakeLogbookRepository implements LogbookRepository {
  final Map<String, LogbookDay> days = {};
  final List<String> keys = [];
  final List<String> calls = [];

  /// Errors to throw, one per call to `createActivity`, in order (null = succeed).
  final List<ApiError?> createErrors = [];
  ApiError? getError;
  int _sequence = 0;

  Logbook _newLogbook(DateTime date) {
    final now = DateTime.utc(2026, 11, 6, 15, 30);
    return Logbook(
      id: 'b${++_sequence}',
      userId: 'p1',
      date: date,
      dateType: date.isBefore(today)
          ? DateType.past
          : (date == today ? DateType.today : DateType.future),
      closed: false,
      summary: '',
      createdAt: now,
      updatedAt: now,
    );
  }

  /// Puts an activity directly in the "server", with the given status.
  void seed(DateTime date, String title, {ActivityStatus status = ActivityStatus.pending, String description = ''}) {
    final key = formatDate(date);
    final day = days[key] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    final id = 'a${++_sequence}';
    final at = DateTime.utc(2026, 11, 6, 15, 31);
    days[key] = LogbookDay(
      logbook: day.logbook,
      plannings: [
        ...day.plannings,
        Planning(
          id: 'pl$id',
          activityId: id,
          date: date,
          type: PlanningType.original,
          description: description,
          createdAt: at,
        ),
      ],
      activities: [
        ...day.activities,
        Activity(
          id: id,
          userId: 'p1',
          title: title,
          origin: ActivityOrigin.planned,
          status: status,
          date: date,
          createdAt: at,
        ),
      ],
    );
  }

  @override
  Future<LogbookDay?> getLogbook(DateTime date) async {
    calls.add('get ${formatDate(date)}');
    final error = getError;
    if (error != null) throw error;
    return days[formatDate(date)];
  }

  @override
  Future<OpenResult> openLogbook(DateTime date) async {
    calls.add('open ${formatDate(date)}');
    final key = formatDate(date);
    final existing = days[key];
    if (existing != null) return OpenResult(created: false, logbook: existing.logbook);
    final logbook = _newLogbook(date);
    days[key] = LogbookDay(logbook: logbook, plannings: const [], activities: const []);
    return OpenResult(created: true, logbook: logbook);
  }

  @override
  Future<PlanResult> createActivity({
    required DateTime date,
    required String title,
    String? description,
    required String key,
  }) async {
    calls.add('create ${formatDate(date)} "$title"');
    keys.add(key);
    if (createErrors.isNotEmpty) {
      final error = createErrors.removeAt(0);
      if (error != null) throw error;
    }
    final dayKey = formatDate(date);
    final created = days[dayKey] == null;
    seed(date, title, description: description ?? '');
    final day = days[dayKey]!;
    return PlanResult(
      activity: day.activities.last,
      planning: day.plannings.last,
      logbookCreated: created,
    );
  }
}
