import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

/// Month grid to pick a date (`.mini-calendar`). Weeks start on Monday. The selected day is
/// filled; today has an outline. There is no "has entries" mark: the API returns one date per
/// query, so the calendar cannot know which other days have activity.
class MiniCalendar extends StatelessWidget {
  const MiniCalendar({
    super.key,
    required this.month,
    required this.selected,
    required this.today,
    required this.onSelect,
  });

  /// Any date of the month to show.
  final DateTime month;
  final DateTime selected;
  final DateTime today;
  final ValueChanged<DateTime> onSelect;

  static const _weekdays = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];

  @override
  Widget build(BuildContext context) {
    final first = DateTime.utc(month.year, month.month, 1);
    final days = DateTime.utc(month.year, month.month + 1, 0).day;
    final offset = first.weekday - 1; // Monday = 0
    final cells = <Widget>[
      for (final d in _weekdays)
        Center(
          child: Text(
            d,
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF9BA7B6)),
          ),
        ),
      for (var i = 0; i < offset; i++) const SizedBox.shrink(),
      for (var d = 1; d <= days; d++)
        _Day(
          key: Key('cal-day-$d'),
          day: d,
          selected: DateTime.utc(month.year, month.month, d) == selected,
          today: DateTime.utc(month.year, month.month, d) == today,
          onTap: () => onSelect(DateTime.utc(month.year, month.month, d)),
        ),
    ];
    return GridView.count(
      crossAxisCount: 7,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      childAspectRatio: 1.25,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: cells,
    );
  }
}

class _Day extends StatelessWidget {
  const _Day({
    super.key,
    required this.day,
    required this.selected,
    required this.today,
    required this.onTap,
  });

  final int day;
  final bool selected;
  final bool today;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: 'Día $day',
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        hoverColor: AppColors.tealSoft,
        onTap: onTap,
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? const Color(0xFF139A91) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: today && !selected ? Border.all(color: const Color(0xFF139A91)) : null,
          ),
          child: Text(
            '$day',
            style: TextStyle(
              fontSize: 11,
              fontWeight: selected || today ? FontWeight.w800 : FontWeight.w400,
              color: selected
                  ? AppColors.white
                  : (today ? const Color(0xFF0B8E83) : const Color(0xFF52637A)),
            ),
          ),
        ),
      ),
    );
  }
}
