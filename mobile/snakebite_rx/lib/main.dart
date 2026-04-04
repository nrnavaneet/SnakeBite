import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'router/app_router.dart';
import 'state/api_session.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(statusBarColor: Colors.transparent),
  );
  final api = ApiSession();
  await api.resolve();
  final router = createAppRouter();
  runApp(
    ChangeNotifierProvider<ApiSession>.value(
      value: api,
      child: SnakeBiteApp(router: router),
    ),
  );
}
