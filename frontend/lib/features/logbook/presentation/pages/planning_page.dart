import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../../core/widgets/buttons.dart';
import '../../../../core/widgets/text_blocks.dart';
import '../providers/side_panel.dart';
import '../widgets/new_activity_panel.dart';

/// "Planificación": where a person goes to plan what they intend to do (M2-03).
///
/// The form itself is the "Nueva actividad" side panel (UX-T3), the same one every screen opens. Arriving here opens it with the
/// PLANNED kind chosen, so the entry of the menu does what its name says without a second form to maintain; closing it leaves this
/// short page with a button to open it again. A planning is not a progress entry: it starts as Pendiente and registers no progress.
class PlanningPage extends ConsumerStatefulWidget {
  const PlanningPage({super.key});

  @override
  ConsumerState<PlanningPage> createState() => _PlanningPageState();
}

class _PlanningPageState extends ConsumerState<PlanningPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && ref.read(sidePanelProvider) == null) openNewActivity(context);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Organiza tu jornada',
          title: 'Planificación',
          subtitle: 'Registra lo que tienes previsto hacer, sin alterar el estado de ejecución.',
          action: PrimaryButton(
            key: const Key('planning-new-activity'),
            label: 'Nueva actividad',
            icon: Icons.add,
            onPressed: () => openNewActivity(context),
          ),
        ),
        const AppCard(
          padding: EdgeInsets.all(AppSpace.xl),
          child: Notice(
            title: 'Una planificación no es un avance',
            text:
                'Planificar una actividad la crea como Pendiente y conserva lo previsto; no registra avances ni cambia su estado. '
                'Los avances se registran después, cuando el trabajo se hace.',
            icon: Icons.info_outline,
          ),
        ),
      ],
    );
  }
}
