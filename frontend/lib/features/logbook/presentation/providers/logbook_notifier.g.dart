// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'logbook_notifier.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// What is persisted for one date. `null` means there is no logbook for it.
///
/// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
/// persisted, not what the client assumes.

@ProviderFor(LogbookNotifier)
const logbookProvider = LogbookNotifierFamily._();

/// What is persisted for one date. `null` means there is no logbook for it.
///
/// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
/// persisted, not what the client assumes.
final class LogbookNotifierProvider
    extends $AsyncNotifierProvider<LogbookNotifier, LogbookDay?> {
  /// What is persisted for one date. `null` means there is no logbook for it.
  ///
  /// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
  /// persisted, not what the client assumes.
  const LogbookNotifierProvider._({
    required LogbookNotifierFamily super.from,
    required DateTime super.argument,
  }) : super(
         retry: null,
         name: r'logbookProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$logbookNotifierHash();

  @override
  String toString() {
    return r'logbookProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  LogbookNotifier create() => LogbookNotifier();

  @override
  bool operator ==(Object other) {
    return other is LogbookNotifierProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$logbookNotifierHash() => r'0c2ee33b1c59de91a86926545c5046785f9c3acc';

/// What is persisted for one date. `null` means there is no logbook for it.
///
/// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
/// persisted, not what the client assumes.

final class LogbookNotifierFamily extends $Family
    with
        $ClassFamilyOverride<
          LogbookNotifier,
          AsyncValue<LogbookDay?>,
          LogbookDay?,
          FutureOr<LogbookDay?>,
          DateTime
        > {
  const LogbookNotifierFamily._()
    : super(
        retry: null,
        name: r'logbookProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  /// What is persisted for one date. `null` means there is no logbook for it.
  ///
  /// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
  /// persisted, not what the client assumes.

  LogbookNotifierProvider call(DateTime date) =>
      LogbookNotifierProvider._(argument: date, from: this);

  @override
  String toString() => r'logbookProvider';
}

/// What is persisted for one date. `null` means there is no logbook for it.
///
/// After every write the state is reloaded FROM THE SERVER, so what the screen shows is what is
/// persisted, not what the client assumes.

abstract class _$LogbookNotifier extends $AsyncNotifier<LogbookDay?> {
  late final _$args = ref.$arg as DateTime;
  DateTime get date => _$args;

  FutureOr<LogbookDay?> build(DateTime date);
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build(_$args);
    final ref = this.ref as $Ref<AsyncValue<LogbookDay?>, LogbookDay?>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<LogbookDay?>, LogbookDay?>,
              AsyncValue<LogbookDay?>,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}
