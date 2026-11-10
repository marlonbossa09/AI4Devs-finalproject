import '../../../../config/app_config.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/utils/dates.dart';
import '../../domain/entities/audit_entities.dart';
import '../../domain/entities/logbook_entities.dart';
import '../models/logbook_models.dart';

/// Calls to the logbook operations of the API (`/mi/...`: always the caller own records).
class LogbookRemoteDataSource {
  LogbookRemoteDataSource(this._client);

  final ApiClient _client;

  static const _base = '${AppConfig.apiPrefix}/mi/bitacoras';

  /// M2-01a. Throws `RECURSO_NO_DISPONIBLE` when there is no logbook for the date.
  Future<LogbookDayModel> getLogbook(DateTime date) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>('$_base/${formatDate(date)}');
      return LogbookDayModel.fromJson(response.data!);
    });
  }

  /// M2-01b.
  Future<OpenResultModel> openLogbook(DateTime date) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        _base,
        data: {'fecha_laboral': formatDate(date)},
      );
      return OpenResultModel.fromJson(response.data!);
    });
  }

  /// M2-02. The whole text is sent as `resumen`; it replaces the previous one. No idempotency key:
  /// repeating a replacement leaves the same result.
  Future<SummaryResultModel> saveSummary({required DateTime date, required String summary}) {
    return _client.guard(() async {
      final response = await _client.dio.put<Map<String, dynamic>>(
        '$_base/${formatDate(date)}/resumen',
        data: {'resumen': summary},
      );
      return SummaryResultModel.fromJson(response.data!);
    });
  }

  /// M2-03. `Idempotency-Key` is mandatory.
  Future<PlanResultModel> createActivity({
    required DateTime date,
    required String title,
    String? description,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '$_base/${formatDate(date)}/planificaciones',
        data: {'titulo': title, if (description != null) 'descripcion': description},
        options: _client.withKey(key),
      );
      return PlanResultModel.fromJson(response.data!);
    });
  }

  /// M2-07. Throws `RECURSO_NO_DISPONIBLE` when it does not exist or is not the user's.
  Future<ActivityDetailModel> getActivity(String id) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>('${AppConfig.apiPrefix}/mi/actividades/$id');
      return ActivityDetailModel.fromJson(response.data!);
    });
  }

  /// M2-08. Only the parameters of the contract: `estado` (repeated, one per status), `limite` and
  /// `continuar_desde`. There is no text search.
  Future<ActivityListModel> listActivities({
    List<ActivityStatus> statuses = const [],
    int? limit,
    String? cursor,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades',
        queryParameters: {
          if (statuses.isNotEmpty) 'estado': [for (final s in statuses) statusToWire(s)],
          'limite': ?limit,
          'continuar_desde': ?cursor,
        },
      );
      return ActivityListModel.fromJson(response.data!);
    });
  }

  /// M2-06. `Idempotency-Key` is mandatory. The body has no origin, no owner and no planning: the
  /// server decides the origin. The block reason only travels with the blocked status.
  Future<ProgressResultModel> registerUnplanned({
    required DateTime date,
    required String title,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades-no-planificadas',
        data: {
          'fecha_laboral': formatDate(date),
          'titulo': title,
          'estado': statusToWire(status),
          'descripcion': description,
          if (status == ActivityStatus.blocked && blockReason != null) 'motivo_bloqueo': blockReason,
        },
        options: _client.withKey(key),
      );
      return ProgressResultModel.fromJson(response.data!);
    });
  }

  /// M3-01. No body; `Idempotency-Key` is mandatory. It never creates the logbook.
  Future<LogbookResultModel> closeLogbook({required DateTime date, required String key}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '$_base/${formatDate(date)}/cierre',
        options: _client.withKey(key),
      );
      return LogbookResultModel.fromJson(response.data!);
    });
  }

  /// M3-02. The only body field is the mandatory `motivo`; `Idempotency-Key` is mandatory.
  Future<LogbookResultModel> reopenLogbook({required DateTime date, required String reason, required String key}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '$_base/${formatDate(date)}/reapertura',
        data: {'motivo': reason},
        options: _client.withKey(key),
      );
      return LogbookResultModel.fromJson(response.data!);
    });
  }

  /// M2-04. `Idempotency-Key` is mandatory. The body has only the date and the optional description:
  /// there is no status (a continuation is a planning, not progress).
  Future<ContinuationResultModel> planContinuation({
    required String activityId,
    required DateTime date,
    String? description,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades/$activityId/continuaciones-planificadas',
        data: {'fecha_laboral': formatDate(date), if (description != null) 'descripcion': description},
        options: _client.withKey(key),
      );
      return ContinuationResultModel.fromJson(response.data!);
    });
  }

  /// M2-05. `Idempotency-Key` is mandatory. The block reason only travels with the blocked status.
  Future<ProgressResultModel> registerProgress({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades/$activityId/avances',
        data: {
          'fecha_laboral': formatDate(date),
          'estado': statusToWire(status),
          'descripcion': description,
          if (status == ActivityStatus.blocked && blockReason != null) 'motivo_bloqueo': blockReason,
        },
        options: _client.withKey(key),
      );
      return ProgressResultModel.fromJson(response.data!);
    });
  }

  /// M3-04. `Idempotency-Key` is mandatory. Same body as a progress entry; the server flags it as a
  /// reactivation and only accepts Pendiente, En progreso or Bloqueada.
  Future<ProgressResultModel> reactivateActivity({
    required String activityId,
    required DateTime date,
    required ActivityStatus status,
    required String description,
    String? blockReason,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades/$activityId/reactivacion',
        data: {
          'fecha_laboral': formatDate(date),
          'estado': statusToWire(status),
          'descripcion': description,
          if (status == ActivityStatus.blocked && blockReason != null) 'motivo_bloqueo': blockReason,
        },
        options: _client.withKey(key),
      );
      return ProgressResultModel.fromJson(response.data!);
    });
  }

  /// M3-05. Marks an activity of the signed-in user as registered by mistake. `Idempotency-Key` is
  /// mandatory; the reason is mandatory too.
  Future<MarkResultModel> markActivityAsError({
    required String activityId,
    required String reason,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades/$activityId/marca-error',
        data: {'motivo': reason},
        options: _client.withKey(key),
      );
      return MarkResultModel.fromJson(response.data!);
    });
  }

  /// M3-06. Removes the mark. No body (no rule asks for a reason to revert); `Idempotency-Key` is mandatory.
  Future<MarkResultModel> revertActivityMark({required String activityId, required String key}) {
    return _client.guard(() async {
      final response = await _client.dio.post<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/actividades/$activityId/marca-error/reversion',
        options: _client.withKey(key),
      );
      return MarkResultModel.fromJson(response.data!);
    });
  }

  /// M3-03. `Idempotency-Key` is mandatory. Only the corrected fields travel: never the work date or an identifier.
  /// The block reason travels only when the entry ends up blocked; correcting to another status makes the
  /// server clear it.
  Future<CorrectionResultModel> correctProgress({
    required String progressId,
    required ProgressCorrection correction,
    required String key,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.patch<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/mi/avances/$progressId',
        data: {
          if (correction.status != null) 'estado': statusToWire(correction.status!),
          if (correction.description != null) 'descripcion': correction.description,
          if (correction.blockReason != null) 'motivo_bloqueo': correction.blockReason,
        },
        options: _client.withKey(key),
      );
      return CorrectionResultModel.fromJson(response.data!);
    });
  }

  /// M3-07. Read-only: `tipo_objeto` and `objeto_id` are mandatory (there is no global audit), plus the optional
  /// `limite` and `continuar_desde`. The operation filter is not used by the app.
  Future<AuditPageModel> listAudit({
    required AuditObjectType type,
    required String objectId,
    int? limit,
    String? cursor,
  }) {
    return _client.guard(() async {
      final response = await _client.dio.get<Map<String, dynamic>>(
        '${AppConfig.apiPrefix}/auditoria',
        queryParameters: {
          'tipo_objeto': auditTypeToWire(type),
          'objeto_id': objectId,
          'limite': ?limit,
          'continuar_desde': ?cursor,
        },
      );
      return AuditPageModel.fromJson(response.data!);
    });
  }
}
