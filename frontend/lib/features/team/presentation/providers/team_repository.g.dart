// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'team_repository.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(teamRepository)
const teamRepositoryProvider = TeamRepositoryProvider._();

final class TeamRepositoryProvider
    extends $FunctionalProvider<TeamRepository, TeamRepository, TeamRepository>
    with $Provider<TeamRepository> {
  const TeamRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'teamRepositoryProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$teamRepositoryHash();

  @$internal
  @override
  $ProviderElement<TeamRepository> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  TeamRepository create(Ref ref) {
    return teamRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(TeamRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<TeamRepository>(value),
    );
  }
}

String _$teamRepositoryHash() => r'e3ef0e854e5b61c973f3139a204edb2ecc8f15c2';
