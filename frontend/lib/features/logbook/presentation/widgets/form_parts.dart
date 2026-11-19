import 'package:flutter/material.dart';

import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_card.dart';

/// Header of a card: title, a line under it and, optionally, the tag that says which kind of record the card holds
/// (planning, execution, continuation...). The tag sits at the end of the title on a wide card and under it on a phone, so a
/// long tag or a large text size never squeezes the title.
class TaggedHeader extends StatelessWidget {
  const TaggedHeader({super.key, required this.title, this.subtitle, this.tag, this.bottom = AppSpace.lg});

  final String title;
  final String? subtitle;
  final Widget? tag;
  final double bottom;

  @override
  Widget build(BuildContext context) {
    final mobile = ScreenSize.ofContext(context).isMobile;
    if (tag == null || !mobile) {
      return PanelHeader(title: title, subtitle: subtitle, trailing: tag, bottom: bottom);
    }
    return Padding(
      padding: EdgeInsets.only(bottom: bottom),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PanelHeader(title: title, subtitle: subtitle, bottom: AppSpace.sm),
          tag!,
        ],
      ),
    );
  }
}

/// A card of a form screen: its header, the fields and, fixed at the bottom, the strip with the actions. The strip is the same
/// on every form, so the actions are always found in the same place.
class FormCard extends StatelessWidget {
  const FormCard({super.key, required this.title, required this.child, this.subtitle, this.tag, this.actions});

  final String title;
  final String? subtitle;
  final Widget? tag;
  final Widget child;

  /// The buttons, already built (see [FormActions]). Without them the card has no strip.
  final Widget? actions;

  static double padding(BuildContext context) => ScreenSize.ofContext(context).isMobile ? AppSpace.lg : AppSpace.xxl;

  @override
  Widget build(BuildContext context) {
    final pad = padding(context);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: EdgeInsets.all(pad),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TaggedHeader(title: title, subtitle: subtitle, tag: tag),
                child,
              ],
            ),
          ),
          if (actions != null)
            Container(
              padding: EdgeInsets.symmetric(horizontal: pad, vertical: AppSpace.md),
              decoration: const BoxDecoration(
                color: AppColors.panelFooter,
                border: Border(top: BorderSide(color: AppColors.border)),
              ),
              child: actions,
            ),
        ],
      ),
    );
  }
}

/// Cancel and submit. On a phone the main action comes first and both take the full width; elsewhere they sit at the end of the
/// strip, cancel first (the reading and keyboard order of every form). They wrap instead of overflowing with a larger text.
class FormActions extends StatelessWidget {
  const FormActions({super.key, required this.cancel, required this.submit});

  final Widget cancel;
  final Widget submit;

  @override
  Widget build(BuildContext context) {
    if (ScreenSize.ofContext(context).isMobile) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [submit, const SizedBox(height: AppSpace.sm), SizedBox(width: double.infinity, child: cancel)],
      );
    }
    return Wrap(
      alignment: WrapAlignment.end,
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: AppSpace.sm,
      runSpacing: AppSpace.sm,
      children: [cancel, submit],
    );
  }
}

/// A form screen is a column no wider than a form needs to be: wider than that the lines are hard to follow.
class FormColumn extends StatelessWidget {
  const FormColumn({super.key, required this.child});

  final Widget child;

  /// Widest a form or a timeline grows.
  static const double maxWidth = 760;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topLeft,
      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: maxWidth), child: child),
    );
  }
}

/// A note under a field or a group of fields: what the action does and does not do.
class FormHint extends StatelessWidget {
  const FormHint(this.text, {super.key, this.textKey});

  final String text;

  /// Key of the text itself, so tests and automation can find it.
  final Key? textKey;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(top: 1),
          child: ExcludeSemantics(child: Icon(Icons.info_outline, size: 16, color: AppColors.textSoft)),
        ),
        const SizedBox(width: AppSpace.sm),
        Expanded(
          child: Text(
            text,
            key: textKey,
            style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
          ),
        ),
      ],
    );
  }
}

/// An error under a form or a list: always a sentence with an icon, never only a color. It is announced when it appears.
class FormErrorText extends StatelessWidget {
  const FormErrorText(this.text, {super.key, this.textKey, this.center = false});

  final String text;
  final Key? textKey;
  final bool center;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Row(
        mainAxisAlignment: center ? MainAxisAlignment.center : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 1),
            child: ExcludeSemantics(child: Icon(Icons.error_outline, size: 16, color: AppColors.error)),
          ),
          const SizedBox(width: AppSpace.sm),
          Flexible(
            child: Text(
              text,
              key: textKey,
              textAlign: center ? TextAlign.center : TextAlign.start,
              style: const TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.error),
            ),
          ),
        ],
      ),
    );
  }
}

/// The record a form is about, shown and never chosen, so the person always knows which one it is: its title, the tags that
/// identify it and a few facts. It is a reference, not a card of its own.
class ContextBox extends StatelessWidget {
  const ContextBox({super.key, required this.title, this.badges = const [], this.details = const [], this.label = 'Actividad'});

  final String label;
  final String title;

  /// Tags and pills, in the order they are read.
  final List<Widget> badges;

  /// Short facts under the tags (dates, the moment of registration).
  final List<Widget> details;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: AppType.caption, color: AppColors.textSoft)),
          const SizedBox(height: 2),
          Text(title, style: const TextStyle(fontSize: AppType.bodyLarge, fontWeight: FontWeight.w800, color: AppColors.ink)),
          if (badges.isNotEmpty) ...[
            const SizedBox(height: AppSpace.sm),
            Wrap(spacing: AppSpace.sm, runSpacing: AppSpace.xs, crossAxisAlignment: WrapCrossAlignment.center, children: badges),
          ],
          if (details.isNotEmpty) ...[
            const SizedBox(height: AppSpace.sm),
            Wrap(spacing: AppSpace.lg, runSpacing: AppSpace.xs, children: details),
          ],
        ],
      ),
    );
  }
}

/// A short fact of a [ContextBox].
class ContextFact extends StatelessWidget {
  const ContextFact(this.text, {super.key, this.strong = false});

  final String text;
  final bool strong;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: TextStyle(
      fontSize: AppType.caption,
      fontWeight: strong ? FontWeight.w800 : FontWeight.w400,
      color: strong ? AppColors.ink : AppColors.textSoft,
    ),
  );
}

/// A load spinner centered in the space a form or a list will take, with the same padding on every screen.
class LoadingBlock extends StatelessWidget {
  const LoadingBlock({super.key});

  @override
  Widget build(BuildContext context) => const Padding(
    padding: EdgeInsets.all(AppSpace.xxl),
    child: Center(child: CircularProgressIndicator()),
  );
}
