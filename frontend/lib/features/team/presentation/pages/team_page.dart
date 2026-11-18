import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/segmented_control.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/team_entities.dart';
import '../../domain/rules/history_range_rules.dart';
import '../providers/team_data.dart';
import '../widgets/history_list.dart';
import '../widgets/peer_logbook_view.dart';

enum _Mode { logbook, history }

/// What the user is reading is a query the server decides: this page only asks and shows (M4-01, M4-02, M4-05). It
/// has no way to write anything and it never decides who may see what.
///
/// Limitation (D-M4-02): the colleague list has the CURRENT members only. Records of someone who already left remain
/// readable in the history without a person filter; there is no picker of former members and no search by name.
class TeamPage extends ConsumerStatefulWidget {
  const TeamPage({super.key});

  @override
  ConsumerState<TeamPage> createState() => _TeamPageState();
}

class _TeamPageState extends ConsumerState<TeamPage> {
  _Mode _mode = _Mode.logbook;

  // Logbook of a colleague
  String? _personId;
  DateTime? _date;
  ({String personId, DateTime date})? _logbookQuery;

  // History
  DateTime? _from;
  DateTime? _to;
  String _historyPerson = _allPeople;
  String? _rangeError;
  ({DateTime from, DateTime to, String? personId})? _historyQuery;

  static const _allPeople = '';

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    _date ??= today;
    _to ??= today;
    _from ??= addDays(today, -6);
    final members = ref.watch(teamMembersProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Equipo',
          title: 'Mi equipo',
          subtitle: 'Lee, solo en lectura, la bitácora de un compañero o el histórico que puedes consultar.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 790),
            child: AppCard(
              padding: EdgeInsets.all(mobile ? 18 : 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SegmentedControl<_Mode>(
                      key: const Key('team-mode'),
                      options: const {_Mode.logbook: 'Bitácora de un compañero', _Mode.history: 'Histórico'},
                      selected: _mode,
                      onChanged: (mode) => setState(() => _mode = mode),
                    ),
                  ),
                  const SizedBox(height: 18),
                  _body(members, session?.user.id, mobile),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _body(AsyncValue<List<TeamMember>> members, String? myId, bool mobile) {
    if (members.isLoading) {
      return const Padding(
        key: Key('team-loading'),
        padding: EdgeInsets.all(32),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (members.hasError) {
      final error = members.error;
      return ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar tu equipo.',
        onRetry: () => ref.invalidate(teamMembersProvider),
      );
    }
    final list = members.value ?? const <TeamMember>[];
    String nameOf(String id) {
      if (id == myId) return 'Tú';
      for (final member in list) {
        if (member.id == id) return member.name;
      }
      // Not in the current team: the client holds no name for them (D-M4-02, limitation).
      return 'Persona que ya no está en tu equipo';
    }

    return _mode == _Mode.logbook ? _logbookTab(list, myId, nameOf) : _historyTab(list, myId, nameOf);
  }

  // ------------------------------------------------------------------------------------------ Bitácora de un compañero

  Widget _logbookTab(List<TeamMember> members, String? myId, String Function(String) nameOf) {
    final colleagues = [for (final m in members) if (m.id != myId) m];
    if (colleagues.isEmpty) {
      return const EmptyState('Todavía no hay otros integrantes en tu equipo.', key: Key('team-no-colleagues'));
    }
    final query = _logbookQuery;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SelectField<String>(
          key: const Key('peer-select'),
          label: 'Compañero',
          hint: 'Elige a un compañero',
          options: {for (final m in colleagues) m.id: m.role == TeamRole.supervisor ? '${m.name} (supervisión)' : m.name},
          value: _personId,
          onChanged: (id) => setState(() {
            _personId = id;
            _logbookQuery = null;
          }),
        ),
        const SizedBox(height: 14),
        DateField(
          fieldKey: const Key('peer-date'),
          label: 'Fecha laboral',
          date: _date!,
          onChanged: (date) => setState(() {
            _date = date;
            _logbookQuery = null;
          }),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: PrimaryButton(
            key: const Key('peer-submit'),
            label: 'Ver bitácora',
            onPressed: _personId == null ? null : _submitLogbook,
          ),
        ),
        const SizedBox(height: 18),
        if (query == null)
          const EmptyState('Elige a un compañero y una fecha para leer su bitácora.', key: Key('peer-none'))
        else
          _PeerLogbookResult(personId: query.personId, date: query.date, ownerName: nameOf(query.personId)),
      ],
    );
  }

  /// Asking is always asking the server again: it never reuses what an earlier answer left in memory, so if the user lost
  /// access in the meantime the answer is the rejection and nothing from before stays on screen.
  void _submitLogbook() {
    ref.invalidate(peerLogbookProvider(_personId!, _date!));
    setState(() => _logbookQuery = (personId: _personId!, date: _date!));
  }

  // ------------------------------------------------------------------------------------------ Histórico

  Widget _historyTab(List<TeamMember> members, String? myId, String Function(String) nameOf) {
    final query = _historyQuery;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('history-from'),
                label: 'Desde',
                date: _from!,
                onChanged: (date) => setState(() {
                  _from = date;
                  _rangeError = null;
                  _historyQuery = null;
                }),
              ),
            ),
            SizedBox(
              width: 220,
              child: DateField(
                fieldKey: const Key('history-to'),
                label: 'Hasta',
                date: _to!,
                errorText: _rangeError,
                onChanged: (date) => setState(() {
                  _to = date;
                  _rangeError = null;
                  _historyQuery = null;
                }),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        SelectField<String>(
          key: const Key('history-person'),
          label: 'Persona (opcional)',
          options: {
            _allPeople: 'Todas las personas que puedo consultar',
            for (final m in members) m.id: m.id == myId ? '${m.name} (tú)' : m.name,
          },
          value: _historyPerson,
          onChanged: (id) => setState(() {
            _historyPerson = id ?? _allPeople;
            _historyQuery = null;
          }),
        ),
        const SizedBox(height: 6),
        Text(
          'El rango es obligatorio y abarca como máximo $maxHistoryRangeDays días. '
          'Sin elegir persona se incluyen también registros de quienes ya salieron del equipo, si puedes consultarlos.',
          key: const Key('history-hint'),
          style: const TextStyle(fontSize: 11, height: 1.5, color: Color(0xFF9BA6B4)),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: PrimaryButton(
            key: const Key('history-submit'),
            label: 'Consultar histórico',
            onPressed: _submitHistory,
          ),
        ),
        const SizedBox(height: 18),
        if (query == null)
          const EmptyState('Elige un rango de fechas para ver el histórico.', key: Key('history-none'))
        else
          _HistoryResult(from: query.from, to: query.to, personId: query.personId, nameOf: nameOf),
      ],
    );
  }

  void _submitHistory() {
    final problem = historyRangeProblem(_from!, _to!);
    if (problem != null) {
      // Not sent: the range is certain to be rejected (the server would say so anyway)
      setState(() {
        _rangeError = historyRangeMessage(problem);
        _historyQuery = null;
      });
      return;
    }
    final personId = _historyPerson == _allPeople ? null : _historyPerson;
    ref.invalidate(historyViewProvider(_from!, _to!, personId));
    setState(() {
      _rangeError = null;
      _historyQuery = (from: _from!, to: _to!, personId: personId);
    });
  }
}

class _PeerLogbookResult extends ConsumerWidget {
  const _PeerLogbookResult({required this.personId, required this.date, required this.ownerName});

  final String personId;
  final DateTime date;
  final String ownerName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(peerLogbookProvider(personId, date));
    if (result.isLoading) {
      return const Padding(
        key: Key('peer-loading'),
        padding: EdgeInsets.all(28),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (result.hasError) {
      final error = result.error;
      return ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar la bitácora.',
        onRetry: () => ref.invalidate(peerLogbookProvider(personId, date)),
      );
    }
    final logbook = result.value;
    if (logbook == null) {
      // The server answers the same for "no logbook" and "not yours to read": the screen does not guess which.
      return const EmptyState(
        'No hay una bitácora disponible de esa persona en esa fecha.',
        key: Key('peer-unavailable'),
      );
    }
    return PeerLogbookView(logbook: logbook, ownerName: ownerName);
  }
}

class _HistoryResult extends ConsumerWidget {
  const _HistoryResult({required this.from, required this.to, required this.personId, required this.nameOf});

  final DateTime from;
  final DateTime to;
  final String? personId;
  final String Function(String) nameOf;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(historyViewProvider(from, to, personId));
    if (result.isLoading) {
      return const Padding(
        key: Key('history-loading'),
        padding: EdgeInsets.all(28),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (result.hasError) {
      final error = result.error;
      return ErrorBox(
        message: error is ApiError ? errorMessage(error) : 'No se pudo cargar el histórico.',
        onRetry: () => ref.invalidate(historyViewProvider(from, to, personId)),
      );
    }
    return HistoryList(
      history: result.value!,
      nameOf: nameOf,
      onLoadMore: () => ref.read(historyViewProvider(from, to, personId).notifier).loadMore(),
    );
  }
}
