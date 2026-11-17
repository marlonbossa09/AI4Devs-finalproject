import 'dart:async';

/// A temporary wait imposed by the server (HTTP 429): the client counts down the time the SERVER communicated
/// and never decides a wait by itself. The device clock is only used to measure elapsed time, never to know
/// the work date.
class Wait {
  const Wait(this.deadline);

  /// Starts a wait of [seconds] from [now].
  factory Wait.from(DateTime now, int seconds) => Wait(now.add(Duration(seconds: seconds)));

  final DateTime deadline;

  /// Whole seconds left, rounded up, never negative. 0 means the wait is over.
  int remainingSeconds(DateTime now) {
    final milliseconds = deadline.difference(now).inMilliseconds;
    return milliseconds <= 0 ? 0 : (milliseconds / 1000).ceil();
  }
}

/// `m:ss` below an hour and `h:mm:ss` from an hour, e.g. `0:29`, `32:00`, `1:00:00`.
String formatWait(int seconds) {
  final total = seconds < 0 ? 0 : seconds;
  final hours = total ~/ 3600;
  final minutes = (total % 3600) ~/ 60;
  final rest = (total % 60).toString().padLeft(2, '0');
  return hours > 0 ? '$hours:${minutes.toString().padLeft(2, '0')}:$rest' : '$minutes:$rest';
}

/// Counts down a [Wait] once per second, reading the clock each time (so a browser tab that throttles its timers still shows the right
/// time) and telling the owner on every tick. Used by the screens that show the 429 wait of the server.
class WaitTicker {
  WaitTicker({required DateTime Function() now, required void Function() onChange}) : _now = now, _onChange = onChange;

  final DateTime Function() _now;
  final void Function() _onChange;
  Wait? _wait;
  Timer? _timer;

  bool get active => _wait != null;

  /// Seconds left of the current wait (0 when there is none).
  int get remaining => _wait?.remainingSeconds(_now()) ?? 0;

  /// Starts (or restarts) a wait of [seconds] and notifies once now.
  void start(int seconds) {
    _timer?.cancel();
    _wait = Wait.from(_now(), seconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tick());
    _onChange();
  }

  void _tick() {
    if (remaining == 0) cancel();
    _onChange();
  }

  void cancel() {
    _timer?.cancel();
    _timer = null;
    _wait = null;
  }
}
