import '../entities/logbook_entities.dart';

/// Whether an activity can be marked as registered by mistake (M3-05, RN-59): it is not marked yet and
/// it has no progress entry in a work day AFTER its origin day (the work date of the logbook where it
/// was created, PA-28; not the moment it was created). Entries on the origin day itself do not prevent it.
///
/// This only mirrors the server rule to offer the action; the server decides. It can still refuse
/// because marking would leave a closed day without a valid activity (`MARCA_INVALIDARIA_CIERRE`).
bool canMarkAsError({required Activity activity, required List<Progress> progress}) =>
    !activity.marked && !hasProgressAfterOrigin(activity: activity, progress: progress);

/// Whether the activity has a progress entry in a day later than its origin day.
bool hasProgressAfterOrigin({required Activity activity, required List<Progress> progress}) =>
    progress.any((entry) => entry.date.isAfter(activity.date));

/// The mark can be reverted only while it is in force (M3-06).
bool canRevertMark(Activity activity) => activity.marked;

/// What is wrong with the reason of a mark (null = fine). The reason is mandatory (RN-59, CA-116).
String? validateMarkReason(String reason) =>
    reason.trim().isEmpty ? 'Indica el motivo por el que se registró por error.' : null;
