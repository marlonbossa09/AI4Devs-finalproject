// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'logbook_repository.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(logbookRepository)
const logbookRepositoryProvider = LogbookRepositoryProvider._();

final class LogbookRepositoryProvider
    extends
        $FunctionalProvider<
          LogbookRepository,
          LogbookRepository,
          LogbookRepository
        >
    with $Provider<LogbookRepository> {
  const LogbookRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'logbookRepositoryProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$logbookRepositoryHash();

  @$internal
  @override
  $ProviderElement<LogbookRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  LogbookRepository create(Ref ref) {
    return logbookRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(LogbookRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<LogbookRepository>(value),
    );
  }
}

String _$logbookRepositoryHash() => r'd574f8bd28ff5c519703b5a87fb5337277752e21';
