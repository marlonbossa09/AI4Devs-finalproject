import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:smartwork/core/errors/api_error.dart';
import 'package:smartwork/core/utils/dates.dart';
import 'package:smartwork/features/auth/domain/entities/session.dart';
import 'package:smartwork/features/auth/domain/repository/auth_repository.dart';
import 'package:smartwork/features/logbook/domain/entities/audit_entities.dart';
import 'package:smartwork/features/logbook/domain/entities/logbook_entities.dart';
import 'package:smartwork/features/logbook/domain/repository/logbook_repository.dart';
import 'package:smartwork/features/logbook/domain/rules/correction_rules.dart';

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

  /// When set, `createActivity` waits for it: lets a test look at the screen while the request is in flight.
  Completer<void>? createGate;
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
    final gate = createGate;
    if (gate != null) await gate.future;
    if (createErrors.isNotEmpty) {
      final error = createErrors.removeAt(0);
      if (error != null) throw error;
    }
    final dayKey = formatDate(date);
    if (days[dayKey]?.logbook.closed == true) {
      throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    }
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

  /// Adds a planned continuation of [activityId] for [date] (a day later than its origin). Like the
  /// server, the day then lists the SAME activity (no copy, no progress).
  void addContinuation(String activityId, DateTime date, String description) {
    final key = formatDate(date);
    final base = days[key] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    final activity = _find(activityId);
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
      activities: activity == null || base.activities.any((a) => a.id == activityId)
          ? base.activities
          : [...base.activities, activity],
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

  // ---- M2-02: daily summary ---------------------------------------------------------------

  /// What `saveSummary` received, one map per call.
  final List<Map<String, Object?>> summaryRequests = [];

  /// Errors to throw, one per call, in order (null = succeed).
  final List<ApiError?> summaryErrors = [];

  /// While set, `saveSummary` waits for it (to look at the screen with the request in flight).
  Completer<void>? summaryGate;

  int _clock = 0;

  /// Closes the logbook of [date] as the server would (the closing operation is not part of the app yet).
  void closeDay(DateTime date) {
    final key = formatDate(date);
    final day = days[key]!;
    final l = day.logbook;
    days[key] = LogbookDay(
      logbook: Logbook(
        id: l.id,
        userId: l.userId,
        date: l.date,
        dateType: l.dateType,
        closed: true,
        summary: l.summary,
        createdAt: l.createdAt,
        updatedAt: l.updatedAt,
        closedAt: DateTime.utc(2026, 11, 6, 18),
      ),
      plannings: day.plannings,
      activities: day.activities,
      progress: day.progress,
    );
  }

  /// Sets the summary of a day directly in the "server" (for the screen to start with one).
  void seedSummary(DateTime date, String summary) {
    final key = formatDate(date);
    final base = days[key] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    days[key] = _withSummary(base, summary, base.logbook.updatedAt);
  }

  LogbookDay _withSummary(LogbookDay day, String summary, DateTime updatedAt) {
    final l = day.logbook;
    return LogbookDay(
      logbook: Logbook(
        id: l.id,
        userId: l.userId,
        date: l.date,
        dateType: l.dateType,
        closed: l.closed,
        summary: summary,
        createdAt: l.createdAt,
        updatedAt: updatedAt,
        closedAt: l.closedAt,
      ),
      plannings: day.plannings,
      activities: day.activities,
      progress: day.progress,
    );
  }

  @override
  Future<SummaryResult> saveSummary({required DateTime date, required String summary}) async {
    calls.add('summary ${formatDate(date)}');
    summaryRequests.add({'date': formatDate(date), 'summary': summary});
    final gate = summaryGate;
    if (gate != null) await gate.future;
    if (summaryErrors.isNotEmpty) {
      final error = summaryErrors.removeAt(0);
      if (error != null) throw error;
    }
    final key = formatDate(date);
    final created = days[key] == null;
    final base = days[key] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    if (base.logbook.closed) {
      throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    }
    // Every save renews the modification moment, even with the same text (RN-18)
    final updated = _withSummary(base, summary, DateTime.utc(2026, 11, 6, 17, 0, ++_clock));
    days[key] = updated;
    return SummaryResult(logbook: updated.logbook, logbookCreated: created);
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
    if (days[dayKey]?.logbook.closed == true) {
      throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    }
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

  // ---- M3-01 and M3-02: closing and reopening the day --------------------------------------

  /// What `closeLogbook` / `reopenLogbook` received, one map per call (including retries).
  final List<Map<String, Object?>> closeRequests = [];
  final List<Map<String, Object?>> reopenRequests = [];

  /// Errors to throw, one per call, in order (null = succeed).
  final List<ApiError?> closeErrors = [];
  final List<ApiError?> reopenErrors = [];

  /// While set, the call waits for it (to look at the screen with the request in flight).
  Completer<void>? closeGate;
  Completer<void>? reopenGate;

  /// The audit entries the "server" would hold: `(operation, reason, date)` in order.
  final List<(String, String?, String)> audit = [];

  final Map<String, (String, Logbook)> _closureByKey = {};

  LogbookDay _withClosure(LogbookDay day, {required bool closed}) {
    final l = day.logbook;
    return LogbookDay(
      logbook: Logbook(
        id: l.id,
        userId: l.userId,
        date: l.date,
        dateType: l.dateType,
        closed: closed,
        summary: l.summary,
        createdAt: l.createdAt,
        updatedAt: l.updatedAt, // closing and reopening do not touch the modification date
        closedAt: closed ? DateTime.utc(2026, 11, 6, 18, 0, ++_clock) : null,
      ),
      plannings: day.plannings,
      activities: day.activities,
      progress: day.progress,
    );
  }

  @override
  Future<Logbook> closeLogbook({required DateTime date, required String key}) async {
    final dayKey = formatDate(date);
    calls.add('close $dayKey');
    closeRequests.add({'date': dayKey, 'key': key});
    final gate = closeGate;
    if (gate != null) await gate.future;
    if (closeErrors.isNotEmpty) {
      final error = closeErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _closureByKey[key];
    if (replay != null) {
      if (replay.$1 != 'close|$dayKey') {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2;
    }
    final day = days[dayKey];
    if (day == null) throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    if (day.logbook.closed) throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    if (date.isAfter(today)) throw const ApiError(code: 'FECHA_FUTURA_NO_PERMITIDA', message: 'x', status: 422);
    // The server's own rule, written out independently of the app's
    final missing = <Map<String, dynamic>>[
      if (day.logbook.summary.trim().isEmpty) {'campo': 'resumen', 'motivo': 'vacio'},
      if (!day.activities.any(
        (a) => !a.marked && (formatDate(a.date) == dayKey || day.progress.any((p) => p.activityId == a.id)),
      ))
        {'campo': 'actividades', 'motivo': 'sin_actividad_creada_ni_continuada'},
    ];
    if (missing.isNotEmpty) {
      throw ApiError(code: 'CONDICIONES_DE_CIERRE_NO_CUMPLIDAS', message: 'x', status: 409, details: missing);
    }
    final closed = _withClosure(day, closed: true);
    days[dayKey] = closed;
    audit.add(('cierre', null, dayKey));
    _closureByKey[key] = ('close|$dayKey', closed.logbook);
    return closed.logbook;
  }

  @override
  Future<Logbook> reopenLogbook({required DateTime date, required String reason, required String key}) async {
    final dayKey = formatDate(date);
    calls.add('reopen $dayKey');
    reopenRequests.add({'date': dayKey, 'reason': reason, 'key': key});
    final gate = reopenGate;
    if (gate != null) await gate.future;
    if (reopenErrors.isNotEmpty) {
      final error = reopenErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _closureByKey[key];
    if (replay != null) {
      if (replay.$1 != 'reopen|$dayKey|$reason') {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2;
    }
    final day = days[dayKey];
    if (day == null) throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    if (reason.trim().isEmpty) throw const ApiError(code: 'MOTIVO_OBLIGATORIO', message: 'x', status: 422);
    if (!day.logbook.closed) throw const ApiError(code: 'BITACORA_NO_CERRADA', message: 'x', status: 409);
    final reopened = _withClosure(day, closed: false);
    days[dayKey] = reopened;
    audit.add(('reapertura', reason, dayKey));
    _closureByKey[key] = ('reopen|$dayKey|$reason', reopened.logbook);
    return reopened.logbook;
  }

  // ---- M2-04: planned continuations --------------------------------------------------------

  /// What `planContinuation` received, one map per call (including retries).
  final List<Map<String, Object?>> continuationRequests = [];

  /// Errors to throw, one per call, in order (null = succeed).
  final List<ApiError?> continuationErrors = [];

  /// While set, `planContinuation` waits for it (to look at the screen with the request in flight).
  Completer<void>? continuationGate;

  final Map<String, (String, ContinuationResult)> _continuationByKey = {};

  @override
  Future<ContinuationResult> planContinuation({
    required String activityId,
    required DateTime date,
    String? description,
    required String key,
  }) async {
    final fingerprint = '$activityId|${formatDate(date)}|${description ?? ''}';
    calls.add('continuation ${formatDate(date)}');
    continuationRequests.add({
      'activityId': activityId,
      'date': formatDate(date),
      'description': description,
      'key': key,
    });
    final gate = continuationGate;
    if (gate != null) await gate.future;
    if (continuationErrors.isNotEmpty) {
      final error = continuationErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _continuationByKey[key];
    if (replay != null) {
      if (replay.$1 != fingerprint) {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2; // the same intention: nothing new is created
    }
    final activity = _find(activityId);
    if (activity == null) throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    // Same order of checks as the server
    if (activity.marked) throw const ApiError(code: 'ACTIVIDAD_MARCADA_POR_ERROR', message: 'x', status: 409);
    if (!date.isAfter(today)) throw const ApiError(code: 'FECHA_NO_FUTURA', message: 'x', status: 422);
    if (activity.status == ActivityStatus.completed) {
      throw const ApiError(code: 'ACTIVIDAD_COMPLETADA', message: 'x', status: 409);
    }
    final dayKey = formatDate(date);
    final logbookCreated = days[dayKey] == null;
    final base = days[dayKey] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    final planning = Planning(
      id: 'pc${++_sequence}',
      activityId: activityId,
      date: date,
      type: PlanningType.continuation,
      description: description ?? '',
      createdAt: DateTime.utc(2026, 11, 6, 16, 10),
    );
    days[dayKey] = LogbookDay(
      logbook: base.logbook,
      plannings: [...base.plannings, planning],
      // the day lists the activity, but no progress is created and the status does not change
      activities: base.activities.any((a) => a.id == activityId) ? base.activities : [...base.activities, activity],
      progress: base.progress,
    );
    final result = ContinuationResult(planning: planning, activity: activity, logbookCreated: logbookCreated);
    _continuationByKey[key] = (fingerprint, result);
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
    if (days[dayKey]?.logbook.closed == true) {
      throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    }
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

  /// What `reactivateActivity` received, one map per call (including retries).
  final List<Map<String, Object?>> reactivationRequests = [];

  /// Errors to throw, one per call to `reactivateActivity`, in order (null = succeed).
  final List<ApiError?> reactivationErrors = [];

  /// While set, `reactivateActivity` waits for it: lets a test look at the screen with the request in flight.
  Completer<void>? reactivationGate;

  final Map<String, (String, ProgressResult)> _reactivationByKey = {};

  /// Same rules as the server (M3-04): own, Completada, not marked, a state other than Completada,
  /// not a future date, not before the completion (the same date is valid), open journal. The new
  /// entry is flagged as a reactivation and sorts AFTER the completion even on the same date.
  @override
  Future<ProgressResult> reactivateActivity({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) async {
    final fingerprint = '$activityId|${formatDate(date)}|${status.name}|$description|${blockReason ?? ''}';
    calls.add('reactivation ${formatDate(date)} ${status.name}');
    reactivationRequests.add({
      'activityId': activityId,
      'date': formatDate(date),
      'status': status,
      'description': description,
      'blockReason': blockReason,
      'key': key,
    });
    final gate = reactivationGate;
    if (gate != null) await gate.future;
    if (reactivationErrors.isNotEmpty) {
      final error = reactivationErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _reactivationByKey[key];
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
    if (activity.marked) {
      throw const ApiError(code: 'ACTIVIDAD_MARCADA_POR_ERROR', message: 'x', status: 409);
    }
    if (status == ActivityStatus.completed) {
      throw const ApiError(code: 'ESTADO_INVALIDO', message: 'x', status: 422);
    }
    final ordered = _progressOf(activityId).toList()
      ..sort((a, b) {
        final byDate = a.date.compareTo(b.date);
        return byDate != 0 ? byDate : _order(a.id).compareTo(_order(b.id));
      });
    if (ordered.isEmpty || ordered.last.status != ActivityStatus.completed) {
      throw const ApiError(code: 'ACTIVIDAD_NO_COMPLETADA', message: 'x', status: 409);
    }
    if (date.isAfter(today)) {
      throw const ApiError(code: 'FECHA_FUTURA_NO_PERMITIDA', message: 'x', status: 422);
    }
    if (date.isBefore(ordered.last.date)) {
      throw const ApiError(code: 'SECUENCIA_INVALIDA', message: 'x', status: 409);
    }
    final dayKey = formatDate(date);
    if (days[dayKey]?.logbook.closed == true) {
      throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    }
    final logbookCreated = days[dayKey] == null;
    final base = days[dayKey] ?? LogbookDay(logbook: _newLogbook(date), plannings: const [], activities: const []);
    final updated = Activity(
      id: activity.id,
      userId: activity.userId,
      title: activity.title,
      origin: activity.origin,
      status: status,
      date: activity.date,
      createdAt: activity.createdAt,
      marked: activity.marked,
      markReason: activity.markReason,
    );
    final entry = Progress(
      id: 'pr${++_sequence}',
      activityId: activityId,
      date: date,
      status: status,
      description: description,
      blockReason: blockReason,
      createdAt: DateTime.utc(2026, 11, 6, 17),
      isReactivation: true,
    );
    days[dayKey] = LogbookDay(
      logbook: base.logbook,
      plannings: base.plannings,
      activities: base.activities.any((a) => a.id == activityId) ? base.activities : [...base.activities, activity],
      progress: [...base.progress, entry],
    );
    // The new status shows in every day where the activity appears.
    for (final k in days.keys.toList()) {
      final day = days[k]!;
      days[k] = LogbookDay(
        logbook: day.logbook,
        plannings: day.plannings,
        activities: [for (final a in day.activities) a.id == activityId ? updated : a],
        progress: day.progress,
      );
    }
    final result = ProgressResult(progress: entry, activity: updated, logbookCreated: logbookCreated);
    _reactivationByKey[key] = (fingerprint, result);
    return result;
  }

  // ------------------------------------------------------------------------------ M3-05 / M3-06

  /// What `markActivityAsError` / `revertActivityMark` received, one map per call (including retries).
  final List<Map<String, Object?>> markRequests = [];

  /// Errors to throw, one per call to either operation, in order (null = succeed).
  final List<ApiError?> markErrors = [];

  /// While set, both operations wait for it: lets a test look at the screen with the request in flight.
  Completer<void>? markGate;

  final Map<String, (String, MarkResult)> _markByKey = {};

  /// Removes the mark behind the screen's back (as if it had been reverted from another place).
  void clearMarkBehindTheScreen(String activityId) => _replaceEverywhere(activityId, (a) => _withMark(a, null));

  void _replaceEverywhere(String activityId, Activity Function(Activity) change) {
    for (final k in days.keys.toList()) {
      final day = days[k]!;
      days[k] = LogbookDay(
        logbook: day.logbook,
        plannings: day.plannings,
        activities: [for (final a in day.activities) a.id == activityId ? change(a) : a],
        progress: day.progress,
      );
    }
  }

  Activity _withMark(Activity a, String? reason) => Activity(
    id: a.id,
    userId: a.userId,
    title: a.title,
    origin: a.origin,
    status: a.status,
    date: a.date,
    createdAt: a.createdAt,
    marked: reason != null,
    markReason: reason,
  );

  Future<void> _markGate(String operation, Map<String, Object?> request) async {
    calls.add(operation);
    markRequests.add(request);
    final gate = markGate;
    if (gate != null) await gate.future;
    if (markErrors.isNotEmpty) {
      final error = markErrors.removeAt(0);
      if (error != null) throw error;
    }
  }

  /// Same rules as the server (M3-05): own activity, mandatory reason, not already marked, no progress
  /// after the origin day, and no closed day left without a valid activity (the origin day AND any day
  /// where the activity counts through its own progress). Nothing is deleted.
  @override
  Future<MarkResult> markActivityAsError({
    required String activityId,
    required String reason,
    required String key,
  }) async {
    await _markGate('mark $activityId', {'activityId': activityId, 'reason': reason, 'key': key});
    final fingerprint = '$activityId|$reason';
    final replay = _markByKey[key];
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
    if (reason.trim().isEmpty) {
      throw const ApiError(code: 'MOTIVO_OBLIGATORIO', message: 'x', status: 422);
    }
    if (activity.marked) {
      throw const ApiError(code: 'ACTIVIDAD_MARCADA_POR_ERROR', message: 'x', status: 409);
    }
    final progress = _progressOf(activityId).toList();
    if (progress.any((p) => p.date.isAfter(activity.date))) {
      throw const ApiError(code: 'MARCA_NO_PROCEDE', message: 'x', status: 409);
    }
    bool counts(Activity other, DateTime date) =>
        other.date == date || _progressOf(other.id).any((p) => p.date == date);
    final affected = {activity.date, ...progress.map((p) => p.date)};
    for (final date in affected) {
      final day = days[formatDate(date)];
      if (day == null || !day.logbook.closed) continue;
      final others = [
        for (final a in _allActivities())
          if (a.id != activityId && !a.marked && counts(a, date)) a,
      ];
      if (others.isEmpty) {
        throw const ApiError(code: 'MARCA_INVALIDARIA_CIERRE', message: 'x', status: 409);
      }
    }
    _replaceEverywhere(activityId, (a) => _withMark(a, reason));
    final result = MarkResult(activity: _find(activityId)!);
    _markByKey[key] = (fingerprint, result);
    return result;
  }

  /// Same rules as the server (M3-06): own activity with a mark in force. The day stays as it was.
  @override
  Future<MarkResult> revertActivityMark({required String activityId, required String key}) async {
    await _markGate('revert $activityId', {'activityId': activityId, 'key': key});
    final replay = _markByKey[key];
    if (replay != null) {
      if (replay.$1 != activityId) {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2;
    }
    final activity = _find(activityId);
    if (activity == null) {
      throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    }
    if (!activity.marked) {
      throw const ApiError(code: 'MARCA_NO_VIGENTE', message: 'x', status: 409);
    }
    _replaceEverywhere(activityId, (a) => _withMark(a, null));
    final result = MarkResult(activity: _find(activityId)!);
    _markByKey[key] = (activityId, result);
    return result;
  }

  // ------------------------------------------------------------------------------------- M3-03

  /// What `correctProgress` received, one map per call (including retries).
  final List<Map<String, Object?>> correctionRequests = [];

  /// Errors to throw, one per call to `correctProgress`, in order (null = succeed).
  final List<ApiError?> correctionErrors = [];

  /// While set, `correctProgress` waits for it: lets a test look at the screen with the request in flight.
  Completer<void>? correctionGate;

  final Map<String, (String, CorrectionResult)> _correctionByKey = {};

  List<Progress> _sequenceOf(String activityId) =>
      _progressOf(activityId).toList()
        ..sort((a, b) {
          final byDate = a.date.compareTo(b.date);
          return byDate != 0 ? byDate : _order(a.id).compareTo(_order(b.id));
        });

  /// Same rules as the server (M3-03): own entry, activity not marked, an open day, a status among the four, a
  /// reason for Bloqueada (cleared for any other status), no new breach of the sequence, and nothing at all when
  /// the values are the ones in force. The entry keeps its identifier, its work date, its moment and its
  /// reactivation flag; nothing is created, removed or reordered. The current status is recalculated from the
  /// last entry of the sequence.
  @override
  Future<CorrectionResult> correctProgress({
    required String progressId,
    required ProgressCorrection correction,
    required String key,
  }) async {
    final fingerprint = '$progressId|${correction.status?.name}|${correction.description}|${correction.blockReason}';
    calls.add('correct $progressId');
    correctionRequests.add({
      'progressId': progressId,
      'status': correction.status,
      'description': correction.description,
      'blockReason': correction.blockReason,
      'key': key,
    });
    final gate = correctionGate;
    if (gate != null) await gate.future;
    if (correctionErrors.isNotEmpty) {
      final error = correctionErrors.removeAt(0);
      if (error != null) throw error;
    }
    final replay = _correctionByKey[key];
    if (replay != null) {
      if (replay.$1 != fingerprint) {
        throw const ApiError(code: 'CLAVE_IDEMPOTENCIA_REUTILIZADA', message: 'x', status: 422);
      }
      return replay.$2;
    }
    Progress? entry;
    for (final candidate in days.values.expand((d) => d.progress)) {
      if (candidate.id == progressId) entry = candidate;
    }
    if (entry == null) throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    final activity = _find(entry.activityId)!;
    if (activity.marked) throw const ApiError(code: 'ACTIVIDAD_MARCADA_POR_ERROR', message: 'x', status: 409);
    if (correction.isEmpty) throw const ApiError(code: 'SOLICITUD_INVALIDA', message: 'x', status: 400);
    final status = correction.status ?? entry.status;
    final description = correction.description ?? entry.description;
    String? reason;
    if (status == ActivityStatus.blocked) {
      reason = correction.blockReason ?? entry.blockReason;
      if (reason == null || reason.trim().isEmpty) {
        throw const ApiError(code: 'MOTIVO_BLOQUEO_OBLIGATORIO', message: 'x', status: 422);
      }
    }
    if (description.trim().isEmpty) throw const ApiError(code: 'DESCRIPCION_OBLIGATORIA', message: 'x', status: 422);
    if (days[formatDate(entry.date)]?.logbook.closed == true) {
      throw const ApiError(code: 'BITACORA_CERRADA', message: 'x', status: 409);
    }
    final sequence = _sequenceOf(entry.activityId);
    CorrectionResult result;
    if (status == entry.status && description == entry.description && reason == entry.blockReason) {
      result = CorrectionResult(progress: entry, activity: activity, currentStatusChanged: false);
    } else {
      if (newSequenceViolations(sequence, entry.id, status).isNotEmpty) {
        throw const ApiError(
          code: 'SECUENCIA_INVALIDA',
          message: 'x',
          status: 409,
          details: [
            {'campo': 'estado', 'motivo': 'avance_tras_finalizacion_sin_reactivacion'},
          ],
        );
      }
      final corrected = Progress(
        id: entry.id,
        activityId: entry.activityId,
        date: entry.date,
        status: status,
        description: description,
        createdAt: entry.createdAt,
        blockReason: reason,
        isReactivation: entry.isReactivation,
        modifiedAt: DateTime.utc(2026, 11, 6, 18),
      );
      final newCurrent = currentStatusAfter(sequence, entry.id, status);
      final changed = newCurrent != activity.status;
      for (final k in days.keys.toList()) {
        final day = days[k]!;
        days[k] = LogbookDay(
          logbook: day.logbook,
          plannings: day.plannings,
          activities: [
            for (final a in day.activities)
              a.id == activity.id
                  ? Activity(
                      id: a.id,
                      userId: a.userId,
                      title: a.title,
                      origin: a.origin,
                      status: newCurrent,
                      date: a.date,
                      createdAt: a.createdAt,
                      marked: a.marked,
                      markReason: a.markReason,
                    )
                  : a,
          ],
          progress: [for (final p in day.progress) p.id == entry.id ? corrected : p],
        );
      }
      result = CorrectionResult(progress: corrected, activity: _find(activity.id)!, currentStatusChanged: changed);
    }
    _correctionByKey[key] = (fingerprint, result);
    return result;
  }

  // ------------------------------------------------------------------------------------- M3-07

  /// The audit "held by the server" for each record, in chronological order, keyed `<type>|<id>`.
  final Map<String, List<AuditEntry>> auditEntries = {};

  /// Records the server says are not available (they do not exist or are someone else's: the same answer).
  final Set<String> auditUnavailable = {};

  /// Page size when the client does not ask for one (the server default).
  int auditPageSize = 20;

  /// What `listAudit` received, one map per call.
  final List<Map<String, Object?>> auditRequests = [];

  /// Errors to throw, one per call to `listAudit`, in order (null = succeed).
  final List<ApiError?> auditErrors = [];

  /// While set, `listAudit` waits for it: lets a test look at the loading state.
  Completer<void>? auditGate;

  String _auditKey(AuditObjectType type, String id) => '${type.name}|$id';

  void seedAudit(AuditObjectType type, String objectId, List<AuditEntry> entries) =>
      auditEntries[_auditKey(type, objectId)] = entries;

  /// Same rules as the server (M3-07): read-only, one record at a time, chronological order, pages by an opaque
  /// cursor, no data and no hint about a record that is not available.
  @override
  Future<AuditPage> listAudit({
    required AuditObjectType type,
    required String objectId,
    int? limit,
    String? cursor,
  }) async {
    calls.add('audit ${type.name} $objectId');
    auditRequests.add({'type': type, 'objectId': objectId, 'limit': limit, 'cursor': cursor});
    final gate = auditGate;
    if (gate != null) await gate.future;
    if (auditErrors.isNotEmpty) {
      final error = auditErrors.removeAt(0);
      if (error != null) throw error;
    }
    final key = _auditKey(type, objectId);
    if (auditUnavailable.contains(key)) {
      throw const ApiError(code: 'RECURSO_NO_DISPONIBLE', message: 'x', status: 404);
    }
    var start = 0;
    if (cursor != null) {
      if (!cursor.startsWith('c')) throw const ApiError(code: 'SOLICITUD_INVALIDA', message: 'x', status: 400);
      start = int.tryParse(cursor.substring(1)) ?? -1;
      if (start < 0) throw const ApiError(code: 'SOLICITUD_INVALIDA', message: 'x', status: 400);
    }
    final all = auditEntries[key] ?? const <AuditEntry>[];
    final size = limit ?? auditPageSize;
    final page = all.skip(start).take(size).toList();
    final more = start + size < all.length;
    return AuditPage(items: page, next: more ? 'c${start + size}' : null);
  }
}
