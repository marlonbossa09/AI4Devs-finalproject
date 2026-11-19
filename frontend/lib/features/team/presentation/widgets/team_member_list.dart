import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/brand.dart';
import '../../../../core/widgets/focus_ring.dart';

/// One row of [TeamMemberList]: a person (or the "everybody" row of the history), with a short line under the name.
class TeamListEntry {
  const TeamListEntry({required this.id, required this.name, this.caption, this.everybody = false});

  /// Value reported when the row is chosen.
  final String id;
  final String name;

  /// What tells this person apart (their role, or that it is the user), in words.
  final String? caption;

  /// The row that stands for "every person the user may read" instead of one person.
  final bool everybody;
}

/// The compact, always visible list of the people of the team (M4-05): who they are and what they are, nothing else.
/// Choosing a row only reports it; this widget reads nothing from the server and shows nothing beyond the name and the
/// role the page gives it. The chosen row is told by a check, by a heavier name and by its background, and a screen
/// reader hears each row as one option of a single-choice group with its selected state.
class TeamMemberList extends StatelessWidget {
  const TeamMemberList({
    super.key,
    required this.title,
    required this.subtitle,
    required this.entries,
    required this.selectedId,
    required this.onSelect,
    this.listKey,
    this.maxHeight = 360,
  });

  final String title;
  final String subtitle;
  final List<TeamListEntry> entries;

  /// The chosen row, or null when none is chosen.
  final String? selectedId;
  final ValueChanged<String> onSelect;

  /// Key of the group of rows, so tests and automation can find it.
  final Key? listKey;

  /// The list scrolls inside this height; a team is small, so it rarely needs to.
  final double maxHeight;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(AppSpace.sm, AppSpace.xs, AppSpace.sm, 0),
            child: Semantics(
              header: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: AppType.cardTitle, fontWeight: FontWeight.w800, color: AppColors.ink)),
                  const SizedBox(height: AppSpace.xs),
                  Text(subtitle, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          ConstrainedBox(
            constraints: BoxConstraints(maxHeight: maxHeight),
            child: SingleChildScrollView(
              child: Column(
                key: listKey,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final entry in entries)
                    _Row(entry: entry, selected: entry.id == selectedId, onTap: () => onSelect(entry.id)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({required this.entry, required this.selected, required this.onTap});

  final TeamListEntry entry;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final caption = entry.caption;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Semantics(
        button: true,
        selected: selected,
        inMutuallyExclusiveGroup: true,
        label: caption == null ? entry.name : '${entry.name}, $caption',
        excludeSemantics: true,
        onTap: onTap,
        child: Material(
          key: Key(entry.everybody ? 'team-member-all' : 'team-member-${entry.id}'),
          color: selected ? AppColors.primarySoft : Colors.transparent,
          borderRadius: BorderRadius.circular(AppRadius.control),
          child: FocusRingInk(
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: AppSize.minTouch + AppSpace.sm),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.sm, vertical: AppSpace.xs + 2),
                child: Row(
                  children: [
                    if (entry.everybody)
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: AppColors.recordedBackground,
                          borderRadius: BorderRadius.circular(AppRadius.card),
                        ),
                        child: const Icon(Icons.groups_outlined, size: 20, color: AppColors.recordedText),
                      )
                    else
                      Avatar(name: entry.name, size: 36),
                    const SizedBox(width: AppSpace.md),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            entry.name,
                            style: TextStyle(
                              fontSize: AppType.body,
                              fontWeight: selected ? FontWeight.w800 : FontWeight.w700,
                              color: AppColors.ink,
                            ),
                          ),
                          if (caption != null)
                            Text(caption, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
                        ],
                      ),
                    ),
                    if (selected) ...[
                      const SizedBox(width: AppSpace.sm),
                      const Icon(Icons.check_circle, size: 18, color: AppColors.primary),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
