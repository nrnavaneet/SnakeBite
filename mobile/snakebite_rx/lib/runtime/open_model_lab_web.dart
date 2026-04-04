import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

/// Opens `web/lab.html` in a new tab, passing the API base as `?api=` when set.
void openModelLab(BuildContext context, String apiBase) {
  final base = Uri.parse(web.window.location.href);
  final path = base.resolve('lab.html');
  final u = apiBase.trim();
  final q = Map<String, String>.from(path.queryParameters);
  if (u.isNotEmpty) {
    q['api'] = u;
  }
  final uri = path.replace(queryParameters: q);
  web.window.open(uri.toString(), '_blank');
}
