import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:snakebite_rx/app.dart';
import 'package:snakebite_rx/router/app_router.dart';
import 'package:snakebite_rx/state/api_session.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('App starts and shows branding', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final api = ApiSession();
    await api.resolve();
    final router = createAppRouter();
    await tester.pumpWidget(
      ChangeNotifierProvider<ApiSession>.value(
        value: api,
        child: SnakeBiteApp(router: router),
      ),
    );
    await tester.pump();
    expect(find.textContaining('SnakeBite'), findsWidgets);
    await tester.pump(const Duration(milliseconds: 2300));
  });
}
