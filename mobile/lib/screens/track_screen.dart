import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../widgets/common.dart';

class TrackScreen extends StatefulWidget {
  const TrackScreen({super.key, this.standalone = false});
  final bool standalone;
  @override
  State<TrackScreen> createState() => _TrackScreenState();
}

class _TrackScreenState extends State<TrackScreen> {
  final _c = TextEditingController();
  Shipment? _result;
  String? _error;
  bool _loading = false;
  static final _re = RegExp(r'^(XD|WD)[A-Z0-9]{10}$');

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  Future<void> _track() async {
    final n = _c.text.trim().toUpperCase();
    setState(() { _result = null; _error = null; });
    if (!_re.hasMatch(n)) {
      setState(() => _error = 'Tracking numbers start with XD followed by 10 letters/numbers.');
      return;
    }
    setState(() => _loading = true);
    try {
      final data = await context.read<ApiClient>().get('/track/$n/', auth: false);
      setState(() => _result = Shipment.fromJson(data as Map<String, dynamic>));
    } on ApiException catch (e) {
      setState(() => _error = e.status == 404 ? 'No parcel found with that tracking number.' : e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _result;
    return Scaffold(
      appBar: AppBar(title: const Text('Track a parcel')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        TextField(
          controller: _c,
          textCapitalization: TextCapitalization.characters,
          maxLength: 12,
          decoration: InputDecoration(
            labelText: 'Tracking number',
            hintText: 'XD7KQ2M9XP4A',
            counterText: '',
            suffixIcon: IconButton(icon: const Icon(Icons.search), onPressed: _loading ? null : _track),
          ),
          onSubmitted: (_) => _track(),
        ),
        const SizedBox(height: 16),
        if (_loading) const Center(child: CircularProgressIndicator()),
        if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
        if (r != null)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(r.trackingNumber, style: const TextStyle(fontFamily: 'monospace', fontSize: 18, fontWeight: FontWeight.bold))),
                  StatusChip(status: r.status, label: r.statusDisplay),
                ]),
                const SizedBox(height: 4),
                Text('${r.route}\n${r.modeDisplay} · ETA ${fmtDate(r.etaDate)}'),
                const SizedBox(height: 12),
                ProgressBarSteps(status: r.status),
                const SizedBox(height: 16),
                Timeline(events: r.events),
              ]),
            ),
          ),
      ]),
    );
  }
}
