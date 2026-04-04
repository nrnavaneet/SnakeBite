import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../state/api_session.dart';
import '../theme/app_theme.dart';
import '../widgets/section_card.dart';
import 'result_screen.dart';

const String _kStaticDisclaimer =
    'SnakeBiteRx is educational software only. It is NOT a medical device and does NOT diagnose '
    'or treat snakebite. Models can make mistakes, including wrong venom type or species. '
    'Wound photos below 60% model confidence are shown as uncertain. '
    'Always call emergency services and follow local protocols; never delay care because of this app.';

class SymptomItem {
  SymptomItem({required this.value, required this.label, required this.category});
  final String value;
  final String label;
  final String category;
  String get display => category.isEmpty ? label : '$category · $label';
}

class AssessScreen extends StatefulWidget {
  const AssessScreen({super.key});

  @override
  State<AssessScreen> createState() => _AssessScreenState();
}

class _AssessScreenState extends State<AssessScreen> {
  final _picker = ImagePicker();
  ApiSession? _apiSession;

  Uint8List? _imageBytes;
  bool _loading = false;
  String? _error;

  bool _bootstrapping = true;

  List<String> _countries = [];
  Map<String, List<String>> _statesByCountry = {};
  bool _regionsLoading = true;
  String _country = 'India';
  String _state = '';

  List<SymptomItem> _symptomItems = [];
  bool _symptomsLoading = true;
  String _symptomQuery = '';
  final Set<String> _selectedSymptoms = {};

  double _timeHours = 3;
  double _age = 35;
  double _weight = 60;
  String _circumstance = 'unknown';

  static const _circumstances = [
    ('unknown', 'Unknown'),
    ('nocturnal_indoor_sleeping', 'Night / indoors / sleeping'),
    ('daytime_outdoor', 'Daytime / outdoors'),
    ('overnight_emns', 'Overnight / EMNS'),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      _apiSession = context.read<ApiSession>();
      await _bootstrap();
      if (!mounted || _apiSession == null) return;
      _apiSession!.addListener(_onApiSessionChanged);
    });
  }

  @override
  void dispose() {
    _apiSession?.removeListener(_onApiSessionChanged);
    super.dispose();
  }

  void _onApiSessionChanged() {
    if (!mounted) return;
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    await context.read<ApiSession>().resolve();
    if (!mounted) return;
    setState(() {
      _regionsLoading = true;
      _symptomsLoading = true;
      _error = null;
    });
    await _loadRegions();
    await _loadSymptoms();
    if (!mounted) return;
    setState(() => _bootstrapping = false);
    WidgetsBinding.instance.addPostFrameCallback((_) => _showDisclaimerIfNeeded());
  }

  Future<void> _showDisclaimerIfNeeded() async {
    final prefs = await SharedPreferences.getInstance();
    if (prefs.getBool('snakebite_disclaimer_v1') == true) return;
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: Icon(Icons.medical_information_outlined, color: Theme.of(ctx).colorScheme.primary),
        title: const Text('Important: read before use'),
        content: SingleChildScrollView(
          child: Text(_kStaticDisclaimer, style: const TextStyle(height: 1.45)),
        ),
        actions: [
          FilledButton(
            onPressed: () async {
              await prefs.setBool('snakebite_disclaimer_v1', true);
              if (ctx.mounted) Navigator.of(ctx).pop();
            },
            child: const Text('I understand'),
          ),
        ],
      ),
    );
  }

  Future<void> _loadRegions() async {
    final api = context.read<ApiSession>();
    if (api.baseUrl.isEmpty) {
      if (!mounted) return;
      setState(() {
        _regionsLoading = false;
        _error = kIsWeb
            ? 'No API URL is configured for this site. Add "apiBase" in web/api_config.json to your '
                'public HTTPS API (then redeploy), or set API_BASE in Vercel. You can also set the URL '
                'in Settings on this device.'
            : 'No API URL is configured. Open Settings and set your backend base URL.';
      });
      return;
    }
    try {
      final r = await http.get(Uri.parse('${api.baseUrl}/geo/regions'));
      if (r.statusCode != 200) throw Exception(r.body);
      final d = jsonDecode(r.body) as Map<String, dynamic>;
      final list = (d['countries'] as List?)?.map((e) => e.toString()).toList() ?? [];
      final raw = d['states_by_country'];
      final map = <String, List<String>>{};
      if (raw is Map) {
        raw.forEach((k, v) {
          if (v is List) {
            map[k.toString()] = v.map((e) => e.toString()).toList();
          }
        });
      }
      setState(() {
        _countries = list;
        _statesByCountry = map;
        _regionsLoading = false;
        if (_countries.contains('India')) _country = 'India';
        _ensureStateValid();
      });
    } catch (e) {
      if (!mounted) return;
      final base = api.baseUrl;
      setState(() {
        _regionsLoading = false;
        _error = kIsWeb
            ? 'Cannot reach the API ($base). On the deployed site, set your public HTTPS URL in '
                'web/api_config.json as "apiBase", or add API_BASE in Vercel → Environment Variables, then redeploy. '
                'Details: $e'
            : 'Could not reach API at $base. Start the server (make api). $e';
      });
    }
  }

  Future<void> _loadSymptoms() async {
    final api = context.read<ApiSession>();
    if (api.baseUrl.isEmpty) {
      if (!mounted) return;
      setState(() => _symptomsLoading = false);
      return;
    }
    try {
      final r = await http.get(Uri.parse('${api.baseUrl}/symptoms'));
      if (r.statusCode != 200) throw Exception(r.body);
      final d = jsonDecode(r.body) as Map<String, dynamic>;
      final raw = d['items'] as List? ?? [];
      final items = <SymptomItem>[];
      for (final x in raw) {
        if (x is Map) {
          items.add(
            SymptomItem(
              value: x['value']?.toString() ?? '',
              label: x['label']?.toString() ?? x['value']?.toString() ?? '',
              category: x['category']?.toString() ?? '',
            ),
          );
        }
      }
      items.sort((a, b) {
        final c = a.category.toLowerCase().compareTo(b.category.toLowerCase());
        if (c != 0) return c;
        return a.label.toLowerCase().compareTo(b.label.toLowerCase());
      });
      setState(() {
        _symptomItems = items;
        _symptomsLoading = false;
        for (final it in items) {
          if (it.value == 'ptosis') _selectedSymptoms.add(it.value);
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _symptomsLoading = false;
        final extra = 'Symptoms could not load: $e';
        _error = _error == null ? extra : '${_error!} $extra';
      });
    }
  }

  void _ensureStateValid() {
    final list = _statesForCountry(_country);
    if (_state.isNotEmpty && !list.contains(_state)) {
      _state = '';
    }
  }

  List<String> _statesForCountry(String c) => _statesByCountry[c] ?? [];

  List<SymptomItem> get _filteredSymptoms {
    final q = _symptomQuery.trim().toLowerCase();
    if (q.isEmpty) return _symptomItems;
    return _symptomItems
        .where(
          (it) =>
              it.display.toLowerCase().contains(q) || it.value.toLowerCase().contains(q),
        )
        .toList();
  }

  Future<void> _pickImage(ImageSource src) async {
    final x = await _picker.pickImage(source: src, imageQuality: 88, maxWidth: 1600);
    if (x == null) return;
    final bytes = await x.readAsBytes();
    if (!mounted) return;
    setState(() => _imageBytes = bytes);
  }

  Future<void> _analyze() async {
    final base = context.read<ApiSession>().baseUrl;
    if (base.isEmpty) {
      setState(() => _error = 'Set the API URL in Settings (or deploy web/api_config.json with apiBase) first.');
      return;
    }
    if (_imageBytes == null) {
      setState(() => _error = 'Add a clear photo of the bite area first.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
    const maxAttempts = 2;
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        if (attempt > 0 && mounted) {
          setState(() => _error = 'Retrying (server may have been waking up)…');
        }
        final uri = Uri.parse('$base/predict');
        final req = http.MultipartRequest('POST', uri);
        req.files.add(http.MultipartFile.fromBytes('file', _imageBytes!, filename: 'wound.jpg'));
        req.fields['symptoms'] = jsonEncode(_selectedSymptoms.toList());
        req.fields['country'] = _country;
        req.fields['state'] = _state;
        req.fields['time_since_bite_hours'] = _timeHours.toString();
        req.fields['bite_circumstance'] = _circumstance;
        req.fields['age_years'] = _age.toString();
        req.fields['weight_kg'] = _weight.toString();

        final streamed = await req.send().timeout(const Duration(seconds: 180));
        final body = await streamed.stream.bytesToString();
        if (streamed.statusCode != 200) {
          throw Exception('HTTP ${streamed.statusCode}: $body');
        }
        final result = jsonDecode(body) as Map<String, dynamic>;
        if (!mounted) return;
        await Navigator.of(context).push<void>(
          PageRouteBuilder<void>(
            transitionDuration: const Duration(milliseconds: 380),
            pageBuilder: (_, animation, __) => ResultScreen(result: result, imageBytes: _imageBytes),
            transitionsBuilder: (_, animation, __, child) {
              return FadeTransition(
                opacity: CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
                child: SlideTransition(
                  position: Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero).animate(
                    CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
                  ),
                  child: child,
                ),
              );
            },
          ),
        );
        break;
      } catch (e) {
        final msg = e.toString();
        final canRetry = kIsWeb &&
            attempt < maxAttempts - 1 &&
            (msg.contains('Failed to fetch') ||
                msg.contains('ClientException') ||
                msg.contains('XMLHttpRequest'));
        if (canRetry) {
          await Future<void>.delayed(const Duration(seconds: 5));
          continue;
        }
        var display = msg;
        if (kIsWeb &&
            (msg.contains('Failed to fetch') ||
                msg.contains('ClientException') ||
                msg.contains('XMLHttpRequest'))) {
          display =
              '$msg\n\n'
              'Often happens if the API host closed the connection: Render Free can be slow to wake, '
              'or run out of RAM during image analysis. Wait a minute after opening the app, try a '
              'smaller photo, check your API service Logs on Render, or upgrade the instance RAM.';
        }
        if (mounted) setState(() => _error = display);
        break;
      }
    }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final session = context.watch<ApiSession>();
    final stateList = _statesForCountry(_country);
    final busy = _loading || _regionsLoading || _bootstrapping;

    if (_bootstrapping) {
      return Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 20),
              Text(
                session.baseUrl.isEmpty
                    ? 'Loading…'
                    : 'Connecting to ${session.baseUrl}…',
                style: TextStyle(color: cs.onSurfaceVariant),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: CustomScrollView(
        slivers: [
          SliverAppBar.large(
            floating: true,
            pinned: false,
            backgroundColor: Colors.transparent,
            surfaceTintColor: Colors.transparent,
            title: const _AppBarBrand(),
            actions: const [],
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 120),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        cs.error.withValues(alpha: 0.12),
                        const Color(0xFFFFF7ED),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: cs.error.withValues(alpha: 0.22)),
                    boxShadow: [
                      BoxShadow(
                        color: cs.error.withValues(alpha: 0.08),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: cs.error.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Icon(Icons.emergency_share_rounded, color: cs.error, size: 26),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Life-threatening emergency?',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w800,
                                color: AppTheme.ink,
                                letterSpacing: -0.2,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Call emergency services first. SnakeBiteRx is educational software, not a substitute for care.',
                              style: TextStyle(
                                fontSize: 13.5,
                                height: 1.45,
                                fontWeight: FontWeight.w500,
                                color: cs.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ).animate().fadeIn(duration: 400.ms).slideX(begin: -0.02, curve: Curves.easeOutCubic),
                const SizedBox(height: 22),
                SectionCard(
                  delayMs: 0,
                  step: 1,
                  title: 'Wound photo',
                  subtitle: 'Bright, steady, in focus. The clearer the photo, the more the models can use.',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: busy ? null : () => _pickImage(ImageSource.gallery),
                              icon: const Icon(Icons.photo_library_outlined),
                              label: const Text('Gallery'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: busy ? null : () => _pickImage(ImageSource.camera),
                              icon: const Icon(Icons.photo_camera_outlined),
                              label: const Text('Camera'),
                            ),
                          ),
                        ],
                      ),
                      if (_imageBytes != null) ...[
                        const SizedBox(height: 16),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(18),
                          child: AspectRatio(
                            aspectRatio: 4 / 3,
                            child: Hero(
                              tag: 'wound_photo',
                              child: Image.memory(_imageBytes!, fit: BoxFit.cover),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                SectionCard(
                  delayMs: 60,
                  step: 2,
                  title: 'Where it happened',
                  subtitle: 'Geo priors refine likely species and venom patterns for that area.',
                  child: Column(
                    children: [
                      if (_regionsLoading) const LinearProgressIndicator(),
                      DropdownButtonFormField<String>(
                        value: _countries.contains(_country) ? _country : (_countries.isNotEmpty ? _countries.first : null),
                        decoration: const InputDecoration(labelText: 'Country'),
                        items: _countries.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                        onChanged: _countries.isEmpty
                            ? null
                            : (v) => setState(() {
                                  _country = v ?? _country;
                                  _ensureStateValid();
                                }),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        value: _state.isEmpty || !stateList.contains(_state) ? '' : _state,
                        decoration: const InputDecoration(
                          labelText: 'State / province',
                          helperText: 'Pick a region if listed, or use the option below.',
                        ),
                        items: [
                          const DropdownMenuItem(
                            value: '',
                            child: Text('My region is not listed (use country level)'),
                          ),
                          ...stateList.map((s) => DropdownMenuItem(value: s, child: Text(s))),
                        ],
                        onChanged: (v) => setState(() => _state = v ?? ''),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                SectionCard(
                  delayMs: 120,
                  step: 3,
                  title: 'Context',
                  subtitle: 'Time since bite and patient factors.',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Hours since bite: ${_timeHours.toStringAsFixed(1)}', style: const TextStyle(fontWeight: FontWeight.w600)),
                      Slider(
                        value: _timeHours,
                        min: 0,
                        max: 72,
                        divisions: 144,
                        onChanged: (v) => setState(() => _timeHours = v),
                      ),
                      DropdownButtonFormField<String>(
                        value: _circumstance,
                        decoration: const InputDecoration(labelText: 'Circumstance'),
                        items: _circumstances
                            .map((e) => DropdownMenuItem(value: e.$1, child: Text(e.$2)))
                            .toList(),
                        onChanged: (v) => setState(() => _circumstance = v ?? 'unknown'),
                      ),
                      Text('Age: ${_age.round()} yrs', style: const TextStyle(fontWeight: FontWeight.w600)),
                      Slider(
                        value: _age,
                        min: 1,
                        max: 100,
                        divisions: 99,
                        onChanged: (v) => setState(() => _age = v),
                      ),
                      Text('Weight: ${_weight.round()} kg', style: const TextStyle(fontWeight: FontWeight.w600)),
                      Slider(
                        value: _weight,
                        min: 5,
                        max: 150,
                        divisions: 145,
                        onChanged: (v) => setState(() => _weight = v),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                SectionCard(
                  delayMs: 180,
                  step: 4,
                  title: 'Signs & symptoms',
                  subtitle: 'Select everything that applies.',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (_symptomsLoading) const LinearProgressIndicator(),
                      TextField(
                        decoration: const InputDecoration(
                          labelText: 'Search',
                          prefixIcon: Icon(Icons.search_rounded),
                          hintText: 'Filter symptoms…',
                        ),
                        onChanged: (v) => setState(() => _symptomQuery = v),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 300,
                        child: _symptomItems.isEmpty && !_symptomsLoading
                            ? const Center(child: Text('No symptoms loaded'))
                            : ListView.separated(
                                itemCount: _filteredSymptoms.length,
                                separatorBuilder: (_, __) => Divider(height: 1, color: cs.outlineVariant.withValues(alpha: 0.35)),
                                itemBuilder: (ctx, i) {
                                  final it = _filteredSymptoms[i];
                                  final sel = _selectedSymptoms.contains(it.value);
                                  return CheckboxListTile(
                                    value: sel,
                                    onChanged: (on) {
                                      setState(() {
                                        if (on == true) {
                                          _selectedSymptoms.add(it.value);
                                        } else {
                                          _selectedSymptoms.remove(it.value);
                                        }
                                      });
                                    },
                                    title: Text(it.display, style: const TextStyle(fontSize: 13.5, height: 1.25)),
                                    dense: true,
                                    controlAffinity: ListTileControlAffinity.leading,
                                  );
                                },
                              ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${_selectedSymptoms.length} selected',
                        style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(54),
                    backgroundColor: AppTheme.primaryDark,
                  ),
                  onPressed: (busy || _symptomsLoading) ? null : _analyze,
                  icon: _loading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.auto_awesome_rounded),
                  label: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Text(
                      _loading ? 'Running fusion…' : 'Run multimodal analysis',
                      style: const TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.2),
                    ),
                  ),
                ).animate().fadeIn(delay: 200.ms),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Material(
                    color: cs.errorContainer.withValues(alpha: 0.45),
                    borderRadius: BorderRadius.circular(14),
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.error_outline_rounded, color: cs.error),
                          const SizedBox(width: 10),
                          Expanded(child: Text(_error!, style: TextStyle(color: cs.onErrorContainer))),
                        ],
                      ),
                    ),
                  ),
                ],
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _AppBarBrand extends StatelessWidget {
  const _AppBarBrand();

  static String _apiSubtitle(String url) {
    try {
      final u = Uri.parse(url);
      if (u.host == '127.0.0.1' || u.host == 'localhost') {
        return 'API: local only. Set web/api_config.json or Vercel API_BASE for the live site';
      }
      return 'API · ${u.host}';
    } catch (_) {
      return url;
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final url = context.watch<ApiSession>().baseUrl;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'SnakeBiteRx',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w900,
                letterSpacing: -0.6,
                color: AppTheme.ink,
              ),
        ),
        const SizedBox(height: 2),
        Text(
          _apiSubtitle(url),
          style: TextStyle(
            fontSize: 11.5,
            color: cs.onSurfaceVariant,
            fontWeight: FontWeight.w600,
            height: 1.25,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}
