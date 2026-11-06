import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Logo mark: a gradient rounded square with an "S" (`.logo-mark`).
class LogoMark extends StatelessWidget {
  const LogoMark({super.key, this.size = 38});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.29),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.logoFrom, AppColors.logoTo],
        ),
      ),
      child: Text('S', style: context.heading(size * 0.55, color: AppColors.white)),
    );
  }
}

/// Circle-ish badge with the initials of a person (`.avatar`).
class Avatar extends StatelessWidget {
  const Avatar({super.key, required this.name, this.size = 38});

  final String name;
  final double size;

  /// "Carlos Colaborador (demo)" -> "CC"
  static String initialsOf(String name) {
    final words = name
        .replaceAll(RegExp(r'\(.*?\)'), '')
        .trim()
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty)
        .toList();
    if (words.isEmpty) return '?';
    if (words.length == 1) return words.first[0].toUpperCase();
    return (words.first[0] + words[1][0]).toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.avatarBackground,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        initialsOf(name),
        style: TextStyle(
          fontSize: size * 0.34,
          fontWeight: FontWeight.w800,
          color: AppColors.avatarText,
        ),
      ),
    );
  }
}
