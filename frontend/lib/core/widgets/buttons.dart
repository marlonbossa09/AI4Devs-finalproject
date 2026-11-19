import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_tokens.dart';
import 'focus_ring.dart';

/// Border that a button draws while it has keyboard focus (a visible 2 px ring, `AppColors.focusRing`).
BorderSide? _focusSide(Set<WidgetState> states, {BorderSide? otherwise, Color ring = AppColors.focusRing}) =>
    states.contains(WidgetState.focused) ? BorderSide(color: ring, width: AppSize.focusRingWidth) : otherwise;

/// Main action button: teal, 8 px corners (`.primary`). 40 px tall (44 on a phone). Disabled it turns neutral grey,
/// not a faded teal; while [loading] it keeps its color and shows a spinner.
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
              if (icon != null) ...[Icon(icon, size: 16), const SizedBox(width: AppSpace.sm)],
              Flexible(child: Text(label, overflow: TextOverflow.ellipsis)),
              if (trailingIcon != null) ...[const SizedBox(width: AppSpace.sm), Icon(trailingIcon, size: 16)],
            ],
          );
    final enabled = onPressed != null && !loading;
    final button = FilledButton(
      onPressed: loading ? null : onPressed,
      style: ButtonStyle(
        backgroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.disabled)) return loading ? AppColors.primary : AppColors.disabledBackground;
          return states.contains(WidgetState.hovered) || states.contains(WidgetState.pressed)
              ? AppColors.primaryHover
              : AppColors.primary;
        }),
        foregroundColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.disabled) && !loading ? AppColors.disabledText : AppColors.white,
        ),
        elevation: const WidgetStatePropertyAll(0),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: AppSpace.lg, vertical: AppSpace.sm)),
        minimumSize: WidgetStatePropertyAll(Size(0, AppSize.control(context))),
        // Without this Material pads every button to a 48 px touch target and the 40/44 px height would not be real.
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: WidgetStateProperty.resolveWith(
          (states) => RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.control),
            side: _focusSide(states, ring: AppColors.focusRingOnPrimary) ?? BorderSide.none,
          ),
        ),
        textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w700)),
      ),
      child: child,
    );
    final shadowed = DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.control),
        boxShadow: enabled ? AppShadow.primaryButton : null,
      ),
      child: button,
    );
    return expand ? SizedBox(width: double.infinity, child: shadowed) : shadowed;
  }
}

/// Secondary action: white with a thin border (`.secondary`). Same height as [PrimaryButton].
class SecondaryButton extends StatelessWidget {
  const SecondaryButton({super.key, required this.label, this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      style: ButtonStyle(
        backgroundColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.disabled)) return AppColors.fieldDisabledBackground;
          return states.contains(WidgetState.hovered) ? AppColors.hoverSurface : AppColors.white;
        }),
        foregroundColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.disabled) ? AppColors.disabledText : AppColors.textBody,
        ),
        side: WidgetStateProperty.resolveWith(
          (states) => _focusSide(states, otherwise: const BorderSide(color: Color(0xFFCBD5E1))),
        ),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: AppSpace.lg, vertical: AppSpace.sm)),
        minimumSize: WidgetStatePropertyAll(Size(0, AppSize.control(context))),
        // Without this Material pads every button to a 48 px touch target and the 40/44 px height would not be real.
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: WidgetStatePropertyAll(RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.control))),
        textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: AppType.body, fontWeight: FontWeight.w700)),
      ),
      child: Text(label),
    );
  }
}

/// Small teal text action (`.text-link`). At least 40 px tall to be a reachable touch target.
class LinkButton extends StatelessWidget {
  const LinkButton({super.key, required this.label, this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onPressed,
      style: ButtonStyle(
        foregroundColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.disabled)
              ? AppColors.disabledText
              : states.contains(WidgetState.hovered)
              ? AppColors.primaryHover
              : AppColors.primary,
        ),
        overlayColor: WidgetStatePropertyAll(AppColors.primarySoft.withValues(alpha: 0.7)),
        padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(horizontal: AppSpace.sm, vertical: AppSpace.sm)),
        minimumSize: const WidgetStatePropertyAll(Size(AppSize.minTouch, AppSize.minTouch)),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: WidgetStateProperty.resolveWith(
          (states) => RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.control),
            side: _focusSide(states) ?? BorderSide.none,
          ),
        ),
        textStyle: const WidgetStatePropertyAll(TextStyle(fontSize: AppType.caption, fontWeight: FontWeight.w700)),
      ),
      child: Text(label),
    );
  }
}

/// Round icon button with a thin border (`.circle-btn`), 40 px. Without [onPressed] it is disabled
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
        child: FocusRingInk(
          onTap: onPressed,
          shape: const CircleBorder(),
          child: Container(
            width: AppSize.minTouch,
            height: AppSize.minTouch,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.white,
              border: Border.all(color: AppColors.border),
            ),
            child: Icon(icon, size: 18, color: onPressed == null ? AppColors.disabledText : AppColors.muted),
          ),
        ),
      ),
    );
  }
}
