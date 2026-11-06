import 'dart:async';
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

  // ---- M2-07 and M2-08: activity detail and list -------------------------------------------

  /// Filters, limit and cursor of every `listActivities` call.
  final List<Map<String, Object?>> listRequests = [];
  final List<String> detailRequests = [];

  /// Errors to throw, one per call, in order (null = succeed).
  final List<ApiError?> listErrors = [];
  final List<ApiError?> detailErrors = [];
  Completer<void>? listGate;
  Completer<void>? detailGate;

  /// One gate per `listActivities` call, consumed in order: lets a test choose which answer
  /// arrives first.
  final List<Completer<void>> listGates = [];

  /// Page size when the client does not ask for one (the server default).
  int defaultPageSize = 20;

  Iterable<Activity> _allActivities() {
    final seen = <String>{};
    return [
      for (final day in days.values)
        for (final activity in day.activities)
          if (seen.add(activity.id)) activity,
    ];
  }

  /// Marks an activity as registered by mistake, in every day where it appears.
  void markAsError(String activityId, {String reason = 'Registrada por error'}) {
    for (final key in days.keys.toList()) {
      final day = days[key]!;
      days[key] = LogbookDay(
        logbook: day.logbook,
        plannings: day.plannings,
        activities: [
          for (final a in day.activities)
            a.id == activityId
                ? Activity(
                    id: a.id,
                    userId: a.userId,
                    title: a.title,
                    origin: a.origin,
                    status: a.status,
                    date: a.date,
                    createdAt: a.createdAt,
                    marked: true,
                    markReason: reason,
                  )
                : a,
        ],
        progress: day.progress,
      );
    }
  }

  /// Adds a planned continuation of [activityId] for [date] (a day later than its origin).
  void addContinuation(String activityId, DateTime date, String description) {
    final key = formatDate(date);
    final base = days[key] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    days[key] = LogbookDay(
      logbook: base.logbook,
      plannings: [
        ...base.plannings,
        Planning(
          id: 'pc${++_sequence}',
          activityId: activityId,
          date: date,
          type: PlanningType.continuation,
          description: description,
          createdAt: DateTime.utc(2026, 11, 6, 15, 40),
        ),
      ],
      activities: base.activities,
      progress: base.progress,
    );
  }

  int _order(String id) => int.tryParse(id.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0;

  @override
  Future<ActivityDetail> getActivity(String id) async {
    calls.add('detail $id');
    detailRequests.add(id);
    final gate = detailGate;
    if (gate != null) await gate.future;
    if (detailErrors.isNotEmpty) {
      final error = detailErrors.removeAt(0);
      if (error != null) throw error;
    }
    final activity = _find(id);
    if (activity == null) throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    final plannings = days.values.expand((d) => d.plannings).where((p) => p.activityId == id).toList()
      ..sort((a, b) => a.date.compareTo(b.date));
    final progress = _progressOf(id).toList()
      ..sort((a, b) {
        final byDate = a.date.compareTo(b.date);
        return byDate != 0 ? byDate : _order(a.id).compareTo(_order(b.id));
      });
    final originals = plannings.where((p) => p.type == PlanningType.original);
    return ActivityDetail(
      activity: activity,
      originalPlanning: originals.isEmpty ? null : originals.first,
      plannedContinuations: plannings.where((p) => p.type == PlanningType.continuation).toList(),
      progress: progress,
      status: activity.status,
    );
  }

  @override
  Future<ActivityListPage> listActivities({
    List<ActivityStatus> statuses = const [],
    int? limit,
    String? cursor,
  }) async {
    calls.add('list');
    listRequests.add({'statuses': statuses, 'limit': limit, 'cursor': cursor});
    final gate = listGate;
    final own = listGates.isEmpty ? null : listGates.removeAt(0);
    if (gate != null) await gate.future;
    if (own != null) await own.future;
    if (listErrors.isNotEmpty) {
      final error = listErrors.removeAt(0);
      if (error != null) throw error;
    }
    // Newest first, never the ones marked as an error, only the requested statuses
    final all = _allActivities().where((a) => !a.marked && (statuses.isEmpty || statuses.contains(a.status))).toList()
      ..sort((a, b) => _order(b.id).compareTo(_order(a.id)));
    final start = cursor == null ? 0 : all.indexWhere((a) => a.id == cursor) + 1;
    final size = limit ?? defaultPageSize;
    final page = all.skip(start).take(size).toList();
    final hasMore = start + size < all.length;
    return ActivityListPage(
      items: [for (final a in page) a.summary],
      next: hasMore ? page.last.id : null,
    );
  }

  // ---- M2-06: unplanned activities --------------------------------------------------------

  /// What `registerUnplanned` received, one map per call (including retries).
  final List<Map<String, Object?>> unplannedRequests = [];

  /// Errors to throw, one per call, in order (null = succeed).
  final List<ApiError?> unplannedErrors = [];

  /// While set, `registerUnplanned` waits for it (to look at the screen with the request in flight).
  Completer<void>? unplannedGate;

  final Map<String, (String, ProgressResult)> _unplannedByKey = {};

  @override
  Future<ProgressResult> registerUnplanned({
    required DateTime date,
    required String title,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final fingerprint = '${formatDate(date)}|$title|${status.name}|$description|${blockReason ?? ''}';
    calls.add('unplanned ${formatDate(date)} "$title"');
    unplannedRequests.add({
      'date': formatDate(date),
      'title': title,
      'status': status,
      'description': description,
      'blockReason': blockReason,
      'key': key,
    });
    final gate = unplannedGate;
    if (gate != null) await gate.future;
    if (unplannedErrors.isNotEmpty) {
      final error = unplannedErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _unplannedByKey[key];
    if (replay != null) {
      if (replay.$1 != fingerprint) {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2; // the same intention: nothing new is created
    }
    final dayKey = formatDate(date);
    final logbookCreated = days[dayKey] == null;
    final base = days[dayKey] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    final activity = Activity(
      id: 'a${++_sequence}',
      userId: 'p1',
      title: title,
      origin: ActivityOrigin.unplanned,
      status: status, // the status of its first progress entry (RN-69)
      date: date,
      createdAt: DateTime.utc(2026, 11, 6, 16, 5),
    );
    final entry = Progress(
      id: 'pr${++_sequence}',
      activityId: activity.id,
      date: date,
      status: status,
      description: description,
      blockReason: blockReason,
      createdAt: DateTime.utc(2026, 11, 6, 16, 5),
    );
    days[dayKey] = LogbookDay(
      logbook: base.logbook,
      plannings: base.plannings, // no planning is created for an unplanned activity
      activities: [...base.activities, activity],
      progress: [...base.progress, entry],
    );
    final result = ProgressResult(progress: entry, activity: activity, logbookCreated: logbookCreated);
    _unplannedByKey[key] = (fingerprint, result);
    return result;
  }

  // ---- M2-05: progress entries -------------------------------------------------------------

  /// What `registerProgress` received, one map per call (including retries).
  final List<Map<String, Object?>> progressRequests = [];

  /// Errors to throw, one per call to `registerProgress`, in order (null = succeed).
  final List<ApiError?> progressErrors = [];

  /// While set, `registerProgress` waits for it: lets a test look at the screen with the request
  /// still in flight.
  Completer<void>? progressGate;

  /// Responses already given, by idempotency key: the same key + the same request returns the
  /// first response and creates nothing new, like the real server.
  final Map<String, (String, ProgressResult)> _byKey = {};

  Iterable<Progress> _progressOf(String activityId) =>
      days.values.expand((day) => day.progress).where((p) => p.activityId == activityId);

  /// Progress entries stored for [activityId], in work-date order.
  List<Progress> progressStored(String activityId) =>
      _progressOf(activityId).toList()..sort((a, b) => a.date.compareTo(b.date));

  Activity? _find(String activityId) {
    for (final day in days.values) {
      for (final activity in day.activities) {
        if (activity.id == activityId) return activity;
      }
    }
    return null;
  }

  @override
  Future<ProgressResult> registerProgress({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final fingerprint = '$activityId|${formatDate(date)}|${status.name}|$description|${blockReason ?? ''}';
    calls.add('progress ${formatDate(date)} ${status.name}');
    progressRequests.add({
      'activityId': activityId,
      'date': formatDate(date),
      'status': status,
      'description': description,
      'blockReason': blockReason,
      'key': key,
    });
    final gate = progressGate;
    if (gate != null) await gate.future;
    if (progressErrors.isNotEmpty) {
      final error = progressErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _byKey[key];
    if (replay != null) {
      if (replay.$1 != fingerprint) {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2;
    }
    final activity = _find(activityId);
    if (activity == null) {
      throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    }
    // Same rule as the server: an entry that would come right after a completion is rejected.
    final before = progressStored(activityId).where((p) => !p.date.isAfter(date)).toList();
    if (before.isNotEmpty && before.last.status == ActivityStatus.completed) {
      throw const ApiError(code: 'ACTIVIDAD_COMPLETADA', message: 'x', status: 409);
    }
    final dayKey = formatDate(date);
    final logbookCreated = days[dayKey] == null;
    final base = days[dayKey] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    final isLast = !_progressOf(activityId).any((p) => p.date.isAfter(date));
    final updated = Activity(
      id: activity.id,
      userId: activity.userId,
      title: activity.title,
      origin: activity.origin,
      status: isLast ? status : activity.status,
      date: activity.date,
      createdAt: activity.createdAt,
    );
    final entry = Progress(
      id: 'pr${++_sequence}',
      activityId: activityId,
      date: date,
      status: status,
      description: description,
      blockReason: blockReason,
      createdAt: DateTime.utc(2026, 11, 6, 16),
    );
    days[dayKey] = LogbookDay(
      logbook: base.logbook,
      plannings: base.plannings,
      activities: base.activities.any((a) => a.id == activityId) ? base.activities : [...base.activities, activity],
      progress: [...base.progress, entry],
    );
    // The new status shows in every day where the activity appears.
    for (final key in days.keys.toList()) {
      final day = days[key]!;
      days[key] = LogbookDay(
        logbook: day.logbook,
        plannings: day.plannings,
        activities: [for (final a in day.activities) a.id == activityId ? updated : a],
        progress: day.progress,
      );
    }
    final result = ProgressResult(progress: entry, activity: updated, logbookCreated: logbookCreated);
    _byKey[key] = (fingerprint, result);
    return result;
  }
}
