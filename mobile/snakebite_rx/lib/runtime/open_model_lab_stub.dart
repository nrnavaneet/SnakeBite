import 'package:flutter/material.dart';

/// Opens the static atomic test page (`web/lab.html`). Web-only implementation opens a new tab.
void openModelLab(BuildContext context, String apiBase) {
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Model lab is only available in the web build (lab.html).')),
  );
}
