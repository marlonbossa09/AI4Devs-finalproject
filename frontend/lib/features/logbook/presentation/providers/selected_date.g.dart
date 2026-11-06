// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'selected_date.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Date the user is looking at. It starts at the server "today" of the current session and is
/// shared by every page, so the dashboard, the logbook and the planning form agree.

@ProviderFor(SelectedDate)
const selectedDateProvider = SelectedDateProvider._();

/// Date the user is looking at. It starts at the server "today" of the current session and is
/// shared by every page, so the dashboard, the logbook and the planning form agree.
final class SelectedDateProvider
    extends $NotifierProvider<SelectedDate, DateTime> {
  /// Date the user is looking at. It starts at the server "today" of the current session and is
  /// shared by every page, so the dashboard, the logbook and the planning form agree.
  const SelectedDateProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'selectedDateProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$selectedDateHash();

  @$internal
  @override
  SelectedDate create() => SelectedDate();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(DateTime value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<DateTime>(value),
    );
  }
}

String _$selectedDateHash() => r'83774a75e230c77a43082723f9e04e0be91857c0';

/// Date the user is looking at. It starts at the server "today" of the current session and is
/// shared by every page, so the dashboard, the logbook and the planning form agree.

abstract class _$SelectedDate extends $Notifier<DateTime> {
  DateTime build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<DateTime, DateTime>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<DateTime, DateTime>,
              DateTime,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
