// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'supervision_repository.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(supervisionRepository)
const supervisionRepositoryProvider = SupervisionRepositoryProvider._();

final class SupervisionRepositoryProvider
    extends
        $FunctionalProvider<
          SupervisionRepository,
          SupervisionRepository,
          SupervisionRepository
        >
    with $Provider<SupervisionRepository> {
  const SupervisionRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'supervisionRepositoryProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$supervisionRepositoryHash();

  @$internal
  @override
  $ProviderElement<SupervisionRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  SupervisionRepository create(Ref ref) {
    return supervisionRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SupervisionRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<SupervisionRepository>(value),
    );
  }
}

String _$supervisionRepositoryHash() =>
    r'a6ed5729d24e4782fb67e98b20407455569faebe';
