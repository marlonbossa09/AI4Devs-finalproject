import 'package:flutter/material.dart';

/// Short confirmation at the bottom right (bottom on mobile), like `.toast` in the design.
void showToast(BuildContext context, String message) {
  final width = MediaQuery.sizeOf(context).width;
  const toastWidth = 380.0;
  final left = width > 600 ? width - toastWidth - 22 : 16.0;
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        content: Text(message),
        duration: const Duration(milliseconds: 2800),
        margin: EdgeInsets.fromLTRB(left, 0, 16, 24),
      ),
    );
}
