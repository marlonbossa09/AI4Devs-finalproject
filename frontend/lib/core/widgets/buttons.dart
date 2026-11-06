import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Main action button: teal, rounded, with a soft shadow (`.primary`).
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.trailingIcon,
    this.loading = false,
    this.expand = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final IconData? trailingIcon;
  final bool loading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final child = loading
        ? const SizedBox(
            height: 18,
            width: 18,
            child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.white),
          )
        : Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[Icon(icon, size: 17), const SizedBox(width: 10)],
              Flexible(child: Text(label, overflow: TextOverflow.ellipsis)),
              if (trailingIcon != null) ...[const SizedBox(width: 10), Icon(trailingIcon, size: 17)],
            ],
          );
    final button = FilledButton(
      onPressed: loading ? null : onPressed,
      style: ButtonStyle(
        backgroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.disabled)) {
            return loading ? AppColors.primary : AppColors.primary.withValues(alpha: 0.45);
          }
          return states.contains(WidgetState.hovered) ? AppColors.primaryHover : AppColors.primary;
        }),
        foregroundColor: const WidgetStatePropertyAll(AppColors.white),
        elevation: const WidgetStatePropertyAll(0),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 18, vertical: 14)),
        minimumSize: const WidgetStatePropertyAll(Size(0, 44)),
        shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
        textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      ),
      child: child,
    );
    final shadowed = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        boxShadow: const [BoxShadow(color: Color(0x24159A8D), blurRadius: 15, offset: Offset(0, 6))],
      ),
      child: button,
    );
    return expand ? SizedBox(width: double.infinity, child: shadowed) : shadowed;
  }
}

/// Secondary action: white with a thin border (`.secondary`).
class SecondaryButton extends StatelessWidget {
  const SecondaryButton({super.key, required this.label, this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      style: ButtonStyle(
        backgroundColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.hovered) ? const Color(0xFFF7FAFB) : AppColors.white,
        ),
        foregroundColor: const WidgetStatePropertyAll(AppColors.textBody),
        side: const WidgetStatePropertyAll(BorderSide(color: Color(0xFFDFE7F0))),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: 16, vertical: 14)),
        minimumSize: const WidgetStatePropertyAll(Size(0, 44)),
        shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
        textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      ),
      child: Text(label),
    );
  }
}

/// Small teal text action (`.text-link`).
class LinkButton extends StatelessWidget {
  const LinkButton({super.key, required this.label, this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onPressed,
      style: TextButton.styleFrom(
        foregroundColor: const Color(0xFF14998F),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
      ),
      child: Text(label),
    );
  }
}

/// Round icon button with a thin border (`.circle-btn`). Without [onPressed] it is disabled
/// and shows [tooltip] to say why.
class CircleIconButton extends StatelessWidget {
  const CircleIconButton({super.key, required this.icon, required this.tooltip, this.onPressed});

  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Semantics(
        button: true,
        enabled: onPressed != null,
        label: tooltip,
        child: InkWell(
          onTap: onPressed,
          customBorder: const CircleBorder(),
          child: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.white,
              border: Border.all(color: AppColors.border),
            ),
            child: Icon(icon, size: 18, color: const Color(0xFF728097)),
          ),
        ),
      ),
    );
  }
}
