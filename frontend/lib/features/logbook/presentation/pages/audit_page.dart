import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../../../auth/presentation/providers/auth.dart';
import '../../domain/entities/audit_entities.dart';
import '../providers/audit_history.dart';
import '../providers/navigation.dart';
import '../widgets/audit_entry_tile.dart';
import '../widgets/audit_tag.dart';

/// The audit of ONE record (M3-07): a timeline of the changes made to it, oldest first, one page at a time.
///
/// - It is NOT the history of the work. The progress history (what was done) lives in the activity detail; the
///   audit says who changed which record, when, why, and what the values were before and after.
/// - It is read-only and shows only what the server returns for the signed-in user's own record. A record that
///   does not exist and one that is someone else's look the same: nothing is revealed about either.
class AuditPage extends ConsumerWidget {
  const AuditPage({super.key});

  String _kindOf(AuditObjectType type) => switch (type) {
    AuditObjectType.logbook => 'la jornada',
    AuditObjectType.activity => 'la actividad',
    AuditObjectType.progress => 'el avance',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final target = ref.watch(auditTargetProvider);
    final currentUserId = ref.watch(authProvider).value?.user.id;

    final back = LinkButton(
      key: const Key('audit-back'),
      label: '← Volver',
      onPressed: () => ref.read(currentPageProvider.notifier).go(target?.back ?? AppPage.logbook),
    );

    Widget body;
    if (target == null) {
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [const EmptyState('Elige un registro para ver su auditoría.', key: Key('audit-none')), back],
      );
    } else {
      final view = ref.watch(auditHistoryProvider(target.type, target.objectId));
      final history = view.value;
      Widget timeline;
      if (view.isLoading && history == null) {
        timeline = const Padding(
          key: Key('audit-loading'),
          padding: EdgeInsets.all(32),
          child: Center(child: CircularProgressIndicator()),
        );
      } else if (view.hasError && history == null) {
        final error = view.error;
        timeline = ErrorBox(
          message: error is ApiError ? _messageOf(error) : 'No se pudo cargar la auditoría.',
          onRetry: () => ref.invalidate(auditHistoryProvider(target.type, target.objectId)),
        );
      } else if (history == null || history.items.isEmpty) {
        timeline = EmptyState(
          'Todavía no hay entradas de auditoría para ${_kindOf(target.type)}. Aparecen cuando se cierra, se reabre, '
          'se corrige, se reactiva o se marca.',
          key: const Key('audit-empty'),
        );
      } else {
        timeline = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var i = 0; i < history.items.length; i++)
              AuditEntryTile(
                entry: history.items[i],
                currentUserId: currentUserId,
                last: i == history.items.length - 1 && !history.hasMore && history.moreError == null,
              ),
            if (history.hasMore || history.moreError != null) ...[
              const SizedBox(height: 16),
              if (history.moreError != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Text(
                    errorMessage(history.moreError!),
                    key: const Key('audit-more-error'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 12, color: AppColors.error),
                  ),
                ),
              Center(
                child: SecondaryButton(
                  key: const Key('audit-load-more'),
                  label: history.loadingMore
                      ? 'Cargando…'
                      : (history.moreError != null ? 'Reintentar' : 'Ver más entradas'),
                  onPressed: history.loadingMore
                      ? null
                      : () => ref.read(auditHistoryProvider(target.type, target.objectId).notifier).loadMore(),
                ),
              ),
            ],
          ],
        );
      }
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            key: const Key('audit-subject'),
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFFAF9FD),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(color: AuditColors.border),
            ),
            child: Wrap(
              spacing: 10,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                const AuditTag(),
                Text(target.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'La auditoría registra quién cambió este registro, cuándo, por qué y qué valores tenía antes y después. '
            'No es el historial de avances del trabajo: ese está en el detalle de la actividad.',
            key: Key('audit-explanation'),
            style: TextStyle(fontSize: 11, height: 1.55, color: AppColors.textSoft),
          ),
          const SizedBox(height: 4),
          const Text(
            'En orden cronológico: lo más antiguo primero.',
            key: Key('audit-order'),
            style: TextStyle(fontSize: 11, color: AppColors.textFaint),
          ),
          const SizedBox(height: 18),
          timeline,
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(padding: const EdgeInsets.only(bottom: 10), child: target == null ? const SizedBox.shrink() : back),
        const PageHeader(
          eyebrow: 'Auditoría',
          title: 'Historial de auditoría',
          subtitle: 'Los cambios hechos a un registro, con su autor, su momento y sus valores anteriores y nuevos.',
        ),
        Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 790),
            child: AppCard(padding: EdgeInsets.all(mobile ? 18 : 24), child: body),
          ),
        ),
      ],
    );
  }

  /// A record that is not available is shown as such, with no hint about whether it exists.
  String _messageOf(ApiError error) => error.code == 'RECURSO_NO_DISPONIBLE'
      ? 'Este registro no está disponible.'
      : errorMessage(error);
}
