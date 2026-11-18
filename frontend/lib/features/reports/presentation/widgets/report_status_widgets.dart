import 'package:flutter/material.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/buttons.dart';

/// A generation in progress. There is NO percentage: the server reports none, so the app only says that it is running. It
/// does not promise a time (a local model can take from tens of seconds to several minutes) and offers no cancel button
/// (there is no cancellation in the contract).
class ReportGenerating extends StatelessWidget {
  const ReportGenerating({super.key});

  @override
  Widget build(BuildContext context) {
    return const Padding(
      key: Key('report-generating'),
      padding: EdgeInsets.symmetric(vertical: 28, horizontal: 8),
      child: Column(
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 14),
          Text(
            'Preparando la solicitud y generando el informe…',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textStrong),
          ),
          SizedBox(height: 6),
          Text(
            'La generación está en curso y puede tardar desde decenas de segundos hasta varios minutos. '
            'No se muestra un avance porque el servidor no lo informa. El informe aparecerá aquí cuando termine.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, height: 1.5, color: AppColors.textSoft),
          ),
        ],
      ),
    );
  }
}

/// Why a report could not be shown. The text is FIXED per error code (see [errorMessage]): it never carries what the server
/// or a model said. A retry is offered ONLY when the server says it can help (`reintento` true); it is always a new action of
/// the user, never automatic. Authorization, validation and limit errors are never retryable.
class ReportFailure extends StatelessWidget {
  const ReportFailure({super.key, required this.error, required this.onRetry});

  final ApiError error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final canRetry = error.retryAllowed == true;
    return Padding(
      key: const Key('report-error'),
      padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 8),
      child: Column(
        children: [
          Text(errorMessage(error), key: const Key('report-error-text'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 13, height: 1.5, color: AppColors.error)),
          if (canRetry) ...[
            const SizedBox(height: 10),
            SecondaryButton(key: const Key('report-retry'), label: 'Intentarlo de nuevo', onPressed: onRetry),
          ],
        ],
      ),
    );
  }
}
