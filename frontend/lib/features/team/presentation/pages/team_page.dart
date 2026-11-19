import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/brand.dart';
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
import '../widgets/team_member_list.dart';

enum _Mode { logbook, history }

/// Width of the list of people when it sits beside the detail (a desktop).
const double _masterWidth = 320;

/// Width from which the fields and the action of a query sit on one line.
const double _wideQueryMinWidth = 620;

String _roleLabel(TeamRole role) => role == TeamRole.supervisor ? 'Supervisor' : 'Colaborador';

/// What the user is reading is a query the server decides: this page only asks and shows (M4-01, M4-02, M4-05). It
/// has no way to write anything and it never decides who may see what.
///
/// Reading order: the two things the page does (a colleague's logbook, or the history), the list of the people of the
/// team, and the detail of what was chosen. On a desktop the list is beside the detail; on a tablet or a phone the detail
/// goes under the list. Nothing is asked of the server for a person until the user asks for it.
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
    final size = ScreenSize.ofContext(context);
    final session = ref.watch(authProvider).value;
    final today = session?.today ?? dateOnly(DateTime.now());
    _date ??= today;
    _to ??= today;
    _from ??= addDays(today, -6);
    final members = ref.watch(teamMembersProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Equipo',
          title: 'Mi equipo',
          subtitle: 'Lee, solo en lectura, la bitácora de un compañero o el histórico que puedes consultar.',
          action: SegmentedControl<_Mode>(
            key: const Key('team-mode'),
            wrap: size.isMobile,
            options: const {_Mode.logbook: 'Bitácora de un compañero', _Mode.history: 'Histórico'},
            selected: _mode,
            onChanged: (mode) => setState(() => _mode = mode),
          ),
        ),
        _body(members, session?.user.id, size),
      ],
    );
  }

  Widget _body(AsyncValue<List<TeamMember>> members, String? myId, ScreenSize size) {
    final pad = size.isMobile ? AppSpace.lg : AppSpace.xl;
    if (members.isLoading) {
      return AppCard(
        child: Padding(
          key: const Key('team-loading'),
          padding: const EdgeInsets.all(AppSpace.xxl + AppSpace.sm),
          child: const Center(child: CircularProgressIndicator(semanticsLabel: 'Cargando tu equipo')),
        ),
      );
    }
    if (members.hasError) {
      final error = members.error;
      return AppCard(
        padding: EdgeInsets.symmetric(horizontal: pad),
        child: ErrorBox(
          message: error is ApiError ? errorMessage(error) : 'No se pudo cargar tu equipo.',
          onRetry: () => ref.invalidate(teamMembersProvider),
        ),
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

    final colleagues = [for (final m in list) if (m.id != myId) m];
    if (_mode == _Mode.logbook && colleagues.isEmpty) {
      return AppCard(
        padding: EdgeInsets.all(pad),
        child: const EmptyState('Todavía no hay otros integrantes en tu equipo.', key: Key('team-no-colleagues')),
      );
    }

    final Widget master;
    final Widget detail;
    if (_mode == _Mode.logbook) {
      master = TeamMemberList(
        key: const Key('team-master'),
        listKey: const Key('peer-select'),
        title: 'Compañeros',
        subtitle: 'Elige a quién quieres leer',
        entries: [for (final m in colleagues) TeamListEntry(id: m.id, name: m.name, caption: _roleLabel(m.role))],
        selectedId: _personId,
        maxHeight: size.isDesktop ? 520 : 320,
        // Choosing a colleague asks for their logbook right away (nothing is asked before that)
        onSelect: (id) {
          setState(() => _personId = id);
          _submitLogbook();
        },
      );
      detail = _logbookDetail(colleagues, nameOf, pad);
    } else {
      master = TeamMemberList(
        key: const Key('team-master'),
        listKey: const Key('history-person'),
        title: 'Personas',
        subtitle: 'Opcional: limita el histórico a una persona',
        entries: [
          const TeamListEntry(id: _allPeople, name: 'Todas las personas que puedo consultar', everybody: true),
          for (final m in list)
            TeamListEntry(
              id: m.id,
              name: m.name,
              caption: m.id == myId ? 'Tú · ${_roleLabel(m.role)}' : _roleLabel(m.role),
            ),
        ],
        selectedId: _historyPerson,
        maxHeight: size.isDesktop ? 520 : 320,
        onSelect: (id) => setState(() {
          _historyPerson = id;
          _historyQuery = null;
        }),
      );
      detail = _historyDetail(list, nameOf, pad);
    }

    if (size.isDesktop) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: _masterWidth, child: master),
          const SizedBox(width: AppSpace.xl),
          Expanded(child: detail),
        ],
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [master, const SizedBox(height: AppSpace.lg), detail]);
  }

  // ------------------------------------------------------------------------------------------ Bitácora de un compañero

  Widget _logbookDetail(List<TeamMember> colleagues, String Function(String) nameOf, double pad) {
    TeamMember? chosen;
    for (final m in colleagues) {
      if (m.id == _personId) chosen = m;
    }
    final query = _logbookQuery;
    return AppCard(
      key: const Key('team-detail'),
      padding: EdgeInsets.all(pad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _DetailHeader(
            person: chosen?.name,
            fallbackIcon: Icons.menu_book_outlined,
            title: chosen?.name ?? 'Bitácora de un compañero',
            subtitle: chosen == null ? 'Solo lectura' : '${_roleLabel(chosen.role)} · bitácora en solo lectura',
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              final narrow = constraints.maxWidth < 480;
              final dateField = DateField(
                fieldKey: const Key('peer-date'),
                label: 'Fecha laboral',
                date: _date!,
                onChanged: (date) {
                  setState(() => _date = date);
                  // With a colleague chosen, another day is asked for at once; without one there is nothing to ask
                  if (_personId == null) {
                    setState(() => _logbookQuery = null);
                  } else {
                    _submitLogbook();
                  }
                },
              );
              final submit = PrimaryButton(
                key: const Key('peer-submit'),
                label: 'Ver bitácora',
                expand: narrow,
                onPressed: _personId == null ? null : _submitLogbook,
              );
              if (narrow) {
                return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [dateField, const SizedBox(height: AppSpace.md), submit]);
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [SizedBox(width: 220, child: dateField), const SizedBox(width: AppSpace.md), submit],
              );
            },
          ),
          const _Rule(),
          if (query == null)
            const EmptyState('Elige a un compañero y una fecha para leer su bitácora.', key: Key('peer-none'))
          else
            _PeerLogbookResult(personId: query.personId, date: query.date, ownerName: nameOf(query.personId)),
        ],
      ),
    );
  }

  /// Asking is always asking the server again: it never reuses what an earlier answer left in memory, so if the user lost
  /// access in the meantime the answer is the rejection and nothing from before stays on screen.
  void _submitLogbook() {
    ref.invalidate(peerLogbookProvider(_personId!, _date!));
    setState(() => _logbookQuery = (personId: _personId!, date: _date!));
  }

  // ------------------------------------------------------------------------------------------ Histórico

  Widget _historyDetail(List<TeamMember> members, String Function(String) nameOf, double pad) {
    final query = _historyQuery;
    final who = _historyPerson == _allPeople ? 'todas las que puedes consultar' : nameOf(_historyPerson);
    return AppCard(
      key: const Key('team-detail'),
      padding: EdgeInsets.all(pad),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _DetailHeader(
            fallbackIcon: Icons.history,
            title: 'Histórico',
            subtitle: 'Persona: $who',
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= _wideQueryMinWidth;
              final from = DateField(
                fieldKey: const Key('history-from'),
                label: 'Desde',
                date: _from!,
                onChanged: (date) => setState(() {
                  _from = date;
                  _rangeError = null;
                  _historyQuery = null;
                }),
              );
              final to = DateField(
                fieldKey: const Key('history-to'),
                label: 'Hasta',
                date: _to!,
                errorText: _rangeError,
                onChanged: (date) => setState(() {
                  _to = date;
                  _rangeError = null;
                  _historyQuery = null;
                }),
              );
              final submit = PrimaryButton(
                key: const Key('history-submit'),
                label: 'Consultar histórico',
                expand: !wide,
                onPressed: _submitHistory,
              );
              if (!wide) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [Expanded(child: from), const SizedBox(width: AppSpace.md), Expanded(child: to)],
                    ),
                    const SizedBox(height: AppSpace.md),
                    submit,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(width: 200, child: from),
                  const SizedBox(width: AppSpace.md),
                  SizedBox(width: 200, child: to),
                  const SizedBox(width: AppSpace.md),
                  _BesideFields(child: submit),
                ],
              );
            },
          ),
          const SizedBox(height: AppSpace.sm),
          Text(
            'El rango es obligatorio y abarca como máximo $maxHistoryRangeDays días. '
            'Sin elegir persona se incluyen también registros de quienes ya salieron del equipo, si puedes consultarlos.',
            key: const Key('history-hint'),
            style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
          ),
          const _Rule(),
          if (query == null)
            const EmptyState('Elige un rango de fechas para ver el histórico.', key: Key('history-none'))
          else
            _HistoryResult(from: query.from, to: query.to, personId: query.personId, nameOf: nameOf),
        ],
      ),
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

/// Who or what the detail is about: the person's initials (or an icon when no one is chosen), the name or the title, and one
/// line under it. The title is read as a heading.
class _DetailHeader extends StatelessWidget {
  const _DetailHeader({this.person, required this.fallbackIcon, required this.title, required this.subtitle});

  final String? person;
  final IconData fallbackIcon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.lg),
      child: Row(
        children: [
          ExcludeSemantics(
            child: person != null
                ? Avatar(name: person!, size: 40)
                : Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(AppRadius.card)),
                    child: Icon(fallbackIcon, size: 22, color: AppColors.primary),
                  ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Semantics(header: true, child: Text(title, style: context.heading(AppType.cardTitle, height: 1.3))),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Puts an action on the same baseline as the fields beside it: it reserves the height of a field label above the action.
class _BesideFields extends StatelessWidget {
  const _BesideFields({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Visibility(visible: false, maintainSize: true, maintainAnimation: true, maintainState: true, child: FieldLabel('Desde')),
        child,
      ],
    );
  }
}

/// Thin line that separates what the user asks from what comes back.
class _Rule extends StatelessWidget {
  const _Rule();

  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.symmetric(vertical: AppSpace.lg),
    child: Divider(height: 1, thickness: 1, color: AppColors.divider),
  );
}

class _Loading extends StatelessWidget {
  const _Loading({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(AppSpace.xxl),
    child: Center(child: CircularProgressIndicator(semanticsLabel: label)),
  );
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
      return const _Loading(key: Key('peer-loading'), label: 'Cargando la bitácora');
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
      return const _Loading(key: Key('history-loading'), label: 'Cargando el histórico');
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
