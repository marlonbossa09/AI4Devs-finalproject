import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/utils/dates.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/confirm_dialog.dart';
import '../../../../core/widgets/fields.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../../core/widgets/toast.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../../logbook/presentation/providers/unsaved_changes.dart';
import '../../../team/domain/entities/team_entities.dart';
import '../../../team/presentation/providers/team_data.dart';
import '../../data/team_admin_remote.dart';

/// Management of the supervisor's own team (M1-11 to M1-13): create a collaborator, give them their code of first access and end their
/// membership. It is a separate functionality from "Mi equipo" (which only READS). Everything is decided by the server: who may do it,
/// which team and which role. The client never sends a team or a role, and an error from the server is shown with a fixed message.
class TeamManagementPage extends ConsumerStatefulWidget {
  const TeamManagementPage({super.key});

  @override
  ConsumerState<TeamManagementPage> createState() => _TeamManagementPageState();
}

class _TeamManagementPageState extends ConsumerState<TeamManagementPage> {
  final _name = TextEditingController();
  final _accessId = TextEditingController();
  bool _busy = false;
  String? _nameError;
  String? _idError;
  String? _error;
  String? _busyMember;
  late final UnsavedGuard _guard = ref.read(unsavedGuardProvider);

  /// Text typed in the form that nothing has saved yet.
  bool _hasUnsaved() => _name.text.trim().isNotEmpty || _accessId.text.trim().isNotEmpty;

  @override
  void initState() {
    super.initState();
    _guard.register(_hasUnsaved);
  }

  @override
  void dispose() {
    _guard.unregister(_hasUnsaved);
    _name.dispose();
    _accessId.dispose();
    super.dispose();
  }

  void _expiredIfNeeded(ApiError error) {
    if (error.isNotSignedIn) ref.read(authProvider.notifier).expired();
  }

  Future<void> _create() async {
    if (_busy) return; // a second tap while the request runs does nothing
    final name = _name.text.trim();
    final accessId = _accessId.text.trim();
    setState(() {
      _nameError = name.isEmpty ? 'Escribe el nombre de la persona.' : null;
      _idError = accessId.isEmpty ? 'Escribe el identificador con el que iniciará sesión.' : null;
      _error = null;
    });
    if (name.isEmpty || accessId.isEmpty) return;
    setState(() => _busy = true);
    final remote = ref.read(teamAdminRemoteProvider);
    String personId;
    try {
      personId = await remote.createCollaborator(name: name, accessId: accessId);
    } on ApiError catch (error) {
      _expiredIfNeeded(error);
      if (mounted) {
        setState(() {
          _busy = false;
          _error = errorMessage(error); // the typed text stays, so it can be fixed and sent again
        });
      }
      return;
    }
    ref.invalidate(teamMembersProvider);
    if (!mounted) return;
    setState(() {
      _name.clear();
      _accessId.clear();
    });
    // The collaborator exists now. The code of first access comes next, and if it fails it can be asked again from the list.
    try {
      final code = await remote.issueFirstAccessCode(personId);
      if (!mounted) return;
      setState(() => _busy = false);
      await _showCode(name: name, accessId: accessId, code: code);
    } on ApiError catch (error) {
      _expiredIfNeeded(error);
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = '$name se creó, pero no se pudo emitir su código: ${errorMessage(error)} Pídelo desde la lista.';
      });
    }
  }

  Future<void> _issueCode(TeamMember member) async {
    if (_busyMember != null) return;
    setState(() {
      _busyMember = member.id;
      _error = null;
    });
    try {
      final code = await ref.read(teamAdminRemoteProvider).issueFirstAccessCode(member.id);
      if (!mounted) return;
      setState(() => _busyMember = null);
      await _showCode(name: member.name, accessId: null, code: code);
    } on ApiError catch (error) {
      _expiredIfNeeded(error);
      if (mounted) {
        setState(() {
          _busyMember = null;
          _error = errorMessage(error);
        });
      }
    }
  }

  Future<void> _end(TeamMember member) async {
    if (_busyMember != null) return;
    final confirmed = await showConfirmDialog(
      context,
      title: '¿Finalizar la pertenencia?',
      message: '${member.name} dejará de ser integrante de tu equipo a partir de mañana. Su historial se conserva y sigue consultable; '
          'hasta entonces sigue en la lista.',
      confirmLabel: 'Finalizar pertenencia',
      cancelLabel: 'Cancelar',
    );
    if (!confirmed || !mounted) return;
    setState(() {
      _busyMember = member.id;
      _error = null;
    });
    try {
      final date = await ref.read(teamAdminRemoteProvider).endMembership(member.id);
      ref.invalidate(teamMembersProvider);
      if (!mounted) return;
      setState(() => _busyMember = null);
      showToast(context, 'La pertenencia de ${member.name} finaliza el ${formatShortDate(date)}.');
    } on ApiError catch (error) {
      _expiredIfNeeded(error);
      if (mounted) {
        setState(() {
          _busyMember = null;
          _error = errorMessage(error);
        });
      }
    }
  }

  /// The code is shown ONCE, here and nowhere else: the server keeps only its HMAC, and the screen does not store it.
  Future<void> _showCode({required String name, required String? accessId, required FirstAccessCode code}) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        key: const Key('code-dialog'),
        title: Text('Código de primer acceso de $name'),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpace.lg),
                decoration: BoxDecoration(
                  color: AppColors.recordedBackground,
                  borderRadius: BorderRadius.circular(AppRadius.control),
                  border: Border.all(color: AppColors.border),
                ),
                child: SelectableText(
                  code.code,
                  key: const Key('code-value'),
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: 1.5, color: AppColors.ink, fontFeatures: [FontFeature.tabularFigures()]),
                ),
              ),
              const SizedBox(height: AppSpace.md),
              if (accessId != null)
                Text('Identificador de acceso: $accessId', style: const TextStyle(fontSize: AppType.body, color: AppColors.textBody)),
              Text('Caduca el ${formatDateTime(code.expiresAt)}.', style: const TextStyle(fontSize: AppType.body, color: AppColors.textBody)),
              const SizedBox(height: AppSpace.md),
              const Notice(
                icon: Icons.info_outline,
                title: 'Se muestra una sola vez',
                text: 'Entrégalo a la persona por un medio que ya uses con ella. Con este código y su identificador, la persona establece su contraseña en '
                    '«Tengo un código de primer acceso», en la pantalla de inicio de sesión. Si lo pierdes, emite uno nuevo: el anterior deja de valer.',
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            key: const Key('code-copy'),
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: code.code));
              if (context.mounted) showToast(context, 'Código copiado.');
            },
            child: const Text('Copiar código'),
          ),
          PrimaryButton(key: const Key('code-done'), label: 'Listo', onPressed: () => Navigator.of(context).pop()),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final size = ScreenSize.ofContext(context);
    final mobile = size.isMobile;
    final members = ref.watch(teamMembersProvider);
    final myId = ref.watch(authProvider).value?.user.id;

    final form = AppCard(
      key: const Key('team-admin-form'),
      padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const PanelHeader(title: 'Nuevo colaborador', subtitle: 'Se crea en tu equipo, con acceso desde hoy'),
          LabeledField(
            fieldKey: const Key('new-member-name'),
            label: 'Nombre',
            hint: 'Ej. Ana Pérez',
            controller: _name,
            enabled: !_busy,
            errorText: _nameError,
            onChanged: (_) => setState(() => _nameError = null),
          ),
          const SizedBox(height: AppSpace.lg),
          LabeledField(
            fieldKey: const Key('new-member-id'),
            label: 'Identificador de acceso',
            hint: 'Ej. ana.perez',
            controller: _accessId,
            enabled: !_busy,
            errorText: _idError,
            onChanged: (_) => setState(() => _idError = null),
            onSubmitted: (_) => _create(),
          ),
          const SizedBox(height: AppSpace.md),
          const Text(
            'La persona será Colaboradora de tu equipo. Al crearla se emite su código de primer acceso, que se muestra una sola vez.',
            style: TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
          ),
          if (_error != null) ...[
            const SizedBox(height: AppSpace.md),
            Semantics(
              liveRegion: true,
              child: Text(_error!, key: const Key('team-admin-error'), style: const TextStyle(fontSize: AppType.body, height: 1.5, color: AppColors.error)),
            ),
          ],
          const SizedBox(height: AppSpace.lg),
          PrimaryButton(
            key: const Key('new-member-submit'),
            label: 'Crear colaborador',
            icon: Icons.person_add_alt_1_outlined,
            loading: _busy,
            expand: true,
            onPressed: _create,
          ),
        ],
      ),
    );

    final list = AppCard(
      key: const Key('team-admin-members'),
      padding: EdgeInsets.all(mobile ? AppSpace.lg : AppSpace.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const PanelHeader(title: 'Integrantes del equipo', subtitle: 'Vigentes hoy'),
          members.when(
            loading: () => const Padding(padding: EdgeInsets.all(AppSpace.xxl), child: Center(child: CircularProgressIndicator())),
            error: (error, _) => ErrorBox(
              message: error is ApiError ? errorMessage(error) : 'No se pudo cargar el equipo.',
              onRetry: () => ref.invalidate(teamMembersProvider),
            ),
            data: (items) => items.isEmpty
                ? const EmptyState('Tu equipo todavía no tiene integrantes.')
                : Column(
                    children: [
                      for (var i = 0; i < items.length; i++)
                        _MemberRow(
                          key: Key('member-${items[i].id}'),
                          member: items[i],
                          itself: items[i].id == myId,
                          busy: _busyMember == items[i].id,
                          first: i == 0,
                          onIssueCode: () => _issueCode(items[i]),
                          onEnd: () => _end(items[i]),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PageHeader(
          eyebrow: 'Equipo',
          title: 'Gestión del equipo',
          subtitle: 'Crea colaboradores en tu equipo, entrega su código de primer acceso y finaliza su pertenencia.',
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            if (size.isDesktop) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: list),
                  const SizedBox(width: AppSpace.xl),
                  SizedBox(width: 380, child: form),
                ],
              );
            }
            return Column(children: [form, SizedBox(height: mobile ? AppSpace.md : AppSpace.lg), list]);
          },
        ),
      ],
    );
  }
}

class _MemberRow extends StatelessWidget {
  const _MemberRow({
    super.key,
    required this.member,
    required this.itself,
    required this.busy,
    required this.first,
    required this.onIssueCode,
    required this.onEnd,
  });

  final TeamMember member;
  final bool itself;
  final bool busy;
  final bool first;
  final VoidCallback onIssueCode;
  final VoidCallback onEnd;

  @override
  Widget build(BuildContext context) {
    final supervisor = member.role == TeamRole.supervisor;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      decoration: BoxDecoration(border: first ? null : const Border(top: BorderSide(color: AppColors.divider))),
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: AppSpace.md,
        runSpacing: AppSpace.xs,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(member.name, style: context.heading(AppType.bodyLarge)),
              Text(
                supervisor ? (itself ? 'Supervisor · tú' : 'Supervisor') : 'Colaborador',
                style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft),
              ),
            ],
          ),
          if (!supervisor)
            Wrap(
              spacing: AppSpace.sm,
              children: [
                LinkButton(key: Key('member-code-${member.id}'), label: busy ? 'Emitiendo…' : 'Emitir código', onPressed: busy ? null : onIssueCode),
                LinkButton(key: Key('member-end-${member.id}'), label: 'Finalizar pertenencia', onPressed: busy ? null : onEnd),
              ],
            ),
        ],
      ),
    );
  }
}
