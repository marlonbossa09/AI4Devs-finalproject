// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'navigation.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Page being shown. It goes back to the dashboard with every new session.

@ProviderFor(CurrentPage)
const currentPageProvider = CurrentPageProvider._();

/// Page being shown. It goes back to the dashboard with every new session.
final class CurrentPageProvider
    extends $NotifierProvider<CurrentPage, AppPage> {
  /// Page being shown. It goes back to the dashboard with every new session.
  const CurrentPageProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'currentPageProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$currentPageHash();

  @$internal
  @override
  CurrentPage create() => CurrentPage();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AppPage value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AppPage>(value),
    );
  }
}

String _$currentPageHash() => r'e8d54a149d6a05131e5ed71c98f550ff8f87f691';

/// Page being shown. It goes back to the dashboard with every new session.

abstract class _$CurrentPage extends $Notifier<AppPage> {
  AppPage build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<AppPage, AppPage>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AppPage, AppPage>,
              AppPage,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
