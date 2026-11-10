import 'package:flutter/material.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/dates.dart';
import '../../domain/entities/audit_entities.dart';
import '../../domain/rules/audit_changes.dart';
import 'audit_tag.dart';

/// One entry of the audit on the timeline: what was done, when, by whom, why, and the values that changed from
/// what they were to what they became (CA-106, CA-108). It carries no action: the audit is read-only.
class AuditEntryTile extends StatelessWidget {
  const AuditEntryTile({super.key, required this.entry, required this.currentUserId, this.last = false});

  final AuditEntry entry;

  /// The signed-in user: the only person ever named ("Tú").
  final String? currentUserId;

  /// The last entry has no line below it.
  final bool last;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    final changes = auditChanges(entry);
    final reason = entry.reason;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // The timeline: a dot and the line that joins it to the next entry
          SizedBox(
            width: 22,
            child: Column(
              children: [
                const SizedBox(height: 6),
                Container(
                  width: 11,
                  height: 11,
                  decoration: BoxDecoration(
                    color: AuditColors.foreground,
                    shape: BoxShape.circle,
                    border: Border.all(color: AuditColors.background, width: 3),
                  ),
                ),
                if (!last) Expanded(child: Container(width: 2, color: AuditColors.border)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: last ? 0 : 20),
              child: Container(
                key: Key('audit-entry-${entry.id}'),
                width: double.infinity,
                padding: EdgeInsets.all(mobile ? 13 : 16),
                decoration: BoxDecoration(
                  color: AppColors.white,
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 12,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          auditOperationLabel(entry),
                          key: Key('audit-operation-${entry.id}'),
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AuditColors.foreground),
                        ),
                        Text(
                          formatDateTime(entry.moment),
                          key: Key('audit-moment-${entry.id}'),
                          style: const TextStyle(fontSize: 11, color: AppColors.textSoft),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 16,
                      runSpacing: 2,
                      children: [
                        Text(
                          'Autor: ${auditAuthorLabel(entry, currentUserId)}',
                          key: Key('audit-author-${entry.id}'),
                          style: const TextStyle(fontSize: 11, color: AppColors.textBody),
                        ),
                        if (entry.workDate != null)
                          Text(
                            'Jornada: ${formatShortDate(entry.workDate!)}',
                            key: Key('audit-workdate-${entry.id}'),
                            style: const TextStyle(fontSize: 11, color: AppColors.textBody),
                          ),
                      ],
                    ),
                    if (reason != null && reason.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Motivo: $reason',
                        key: Key('audit-reason-${entry.id}'),
                        style: const TextStyle(fontSize: 12, height: 1.5, fontWeight: FontWeight.w700, color: AppColors.textBody),
                      ),
                    ],
                    if (changes.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      for (var i = 0; i < changes.length; i++)
                        _ChangeLine(key: Key('audit-change-${entry.id}-$i'), change: changes[i], stacked: mobile),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// One changed value: its label, what it was and what it became. A missing value is shown as a dash.
class _ChangeLine extends StatelessWidget {
  const _ChangeLine({super.key, required this.change, required this.stacked});

  final AuditChange change;

  /// On a narrow screen the two values go one below the other.
  final bool stacked;

  @override
  Widget build(BuildContext context) {
    Widget value(String title, String? text, Key key, Color color) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 9.5, letterSpacing: 0.6, color: AppColors.textFaint)),
        const SizedBox(height: 2),
        Text(text ?? '—', key: key, style: TextStyle(fontSize: 12, height: 1.45, color: color)),
      ],
    );
    final before = value('ANTES', change.before, const Key('audit-before'), AppColors.textSoft);
    final after = value('AHORA', change.after, const Key('audit-after'), AppColors.ink);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: const Color(0xFFFAF9FD),
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: AuditColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            change.label,
            key: const Key('audit-label'),
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AuditColors.foreground),
          ),
          const SizedBox(height: 6),
          if (stacked)
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [before, const SizedBox(height: 8), after])
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: before),
                const Padding(
                  padding: EdgeInsets.fromLTRB(10, 14, 10, 0),
                  child: Icon(Icons.arrow_forward, size: 14, color: AppColors.textFaint),
                ),
                Expanded(child: after),
              ],
            ),
        ],
      ),
    );
  }
}
