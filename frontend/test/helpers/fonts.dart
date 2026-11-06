import 'dart:io';

import 'package:flutter/services.dart';

/// Widget tests draw text with the "Ahem" font, where every letter is a full square. That makes
/// text about twice as wide as in a browser and reports overflows that do not exist. This loads
/// the real Roboto font that ships with the Flutter SDK so layout tests are realistic.
Future<void> loadTestFonts() async {
  final root = _flutterRoot();
  if (root == null) return;
  final dir = '$root/bin/cache/artifacts/material_fonts';
  final loader = FontLoader('Roboto');
  var any = false;
  for (final name in ['roboto-regular.ttf', 'roboto-medium.ttf', 'roboto-bold.ttf', 'roboto-black.ttf']) {
    final file = File('$dir/$name');
    if (file.existsSync()) {
      loader.addFont(Future.value(ByteData.view(file.readAsBytesSync().buffer)));
      any = true;
    }
  }
  if (any) await loader.load();
}

String? _flutterRoot() {
  final env = Platform.environment['FLUTTER_ROOT'];
  if (env != null && Directory(env).existsSync()) return env;
  // .../flutter/bin/cache/dart-sdk/bin/dart(.exe)
  final parts = Platform.resolvedExecutable.replaceAll('\\', '/').split('/');
  final index = parts.indexOf('cache');
  if (index > 1) return parts.sublist(0, index - 1).join('/');
  return null;
}
