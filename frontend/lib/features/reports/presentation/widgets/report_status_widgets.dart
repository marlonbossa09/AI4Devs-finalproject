import 'package:flutter/material.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/layout/screen_size.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';

EdgeInsets _padding(BuildContext context) => EdgeInsets.all(ScreenSize.ofContext(context).isMobile ? AppSpace.lg : AppSpace.xl);

/// A generation in progress. There is NO percentage: the server reports none, so the app only says that it is running. It
/// does not promise a time (a local model can take from tens of seconds to several minutes) and offers no cancel button
/// (there is no cancellation in the contract). It is a polite live region: a screen reader says when it starts.
class ReportGenerating extends StatelessWidget {
  const ReportGenerating({super.key});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      container: true,
      child: AppCard(
        key: const Key('report-generating'),
        padding: _padding(context),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 3)),
            const SizedBox(width: AppSpace.lg),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Preparando la solicitud y generando el informe…', style: context.heading(AppType.bodyLarge, color: AppColors.textStrong, height: 1.3)),
                  const SizedBox(height: AppSpace.xs + 2),
                  const Text(
                    'La generación está en curso y puede tardar desde decenas de segundos hasta varios minutos. '
                    'No se muestra un avance porque el servidor no lo informa. El informe aparecerá aquí cuando termine.',
                    style: TextStyle(fontSize: AppType.caption, height: 1.5, color: AppColors.textSoft),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Why a report could not be shown. The text is FIXED per error code (see [errorMessage]): it never carries what the server
/// or a model said. A retry is offered ONLY when the server says it can help (`reintento` true); it is always a new action of
/// the user, never automatic. Authorization, validation and limit errors are never retryable. It says that the report could not
/// be generated and shows nothing of any earlier or partial report. It is a polite live region.
class ReportFailure extends StatelessWidget {
  const ReportFailure({super.key, required this.error, required this.onRetry});

  final ApiError error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final canRetry = error.retryAllowed == true;
    return Semantics(
      liveRegion: true,
      container: true,
      child: AppCard(
        key: const Key('report-error'),
        padding: _padding(context),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(color: AppColors.blockedBackground, borderRadius: BorderRadius.circular(AppRadius.control)),
              child: const ExcludeSemantics(child: Icon(Icons.error_outline, size: 20, color: AppColors.blockedText)),
            ),
            const SizedBox(width: AppSpace.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('No se pudo generar el informe', style: context.heading(AppType.bodyLarge, color: AppColors.textStrong, height: 1.3)),
                  const SizedBox(height: AppSpace.xs),
                  Text(
                    errorMessage(error),
                    key: const Key('report-error-text'),
                    style: const TextStyle(fontSize: AppType.body, height: 1.5, color: AppColors.error),
                  ),
                  if (canRetry) ...[
                    const SizedBox(height: AppSpace.md),
                    SecondaryButton(key: const Key('report-retry'), label: 'Intentarlo de nuevo', onPressed: onRetry),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
