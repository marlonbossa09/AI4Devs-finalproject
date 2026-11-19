import 'package:flutter/material.dart';

/// Short confirmation at the bottom right (bottom on mobile), like `.toast` in the design.
void showToast(BuildContext context, String message) =>
    showToastOn(ScaffoldMessenger.of(context), MediaQuery.sizeOf(context).width, message);

/// The same confirmation, shown on a messenger captured earlier: for a panel that closes itself and whose own context is gone by the
/// time the server answers.
void showToastOn(ScaffoldMessengerState messenger, double width, String message) {
  const toastWidth = 380.0;
  final left = width > 600 ? width - toastWidth - 22 : 16.0;
  messenger
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(milliseconds: 2800),
        margin: EdgeInsets.fromLTRB(left, 0, 16, 24),
      ),
    );
}
