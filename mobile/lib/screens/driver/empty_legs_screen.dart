import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../models/driver_models.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import '../../widgets/place_picker.dart';

/// "I'm going back empty": a driver offers return space so operations can fill it.
class EmptyLegsScreen extends StatefulWidget {
  const EmptyLegsScreen({super.key});
  @override
  State<EmptyLegsScreen> createState() => _EmptyLegsScreenState();
}

class _EmptyLegsScreenState extends State<EmptyLegsScreen> {
  List<EmptyLeg>? _legs;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await context.read<ApiClient>().get('/driver/empty-legs/', query: {'page_size': '50'}) as Map;
      if (!mounted) return;
      setState(() {
        _legs = (res['results'] as List).map((e) => EmptyLeg.fromJson(e as Map<String, dynamic>)).toList();
        _error = null;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _new() async {
    final created = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const _EmptyLegForm()));
    if (created == true) {
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sent to operations. We will call you when we have cargo for this trip.')));
    }
  }

  Future<void> _withdraw(EmptyLeg l) async {
    try {
      await context.read<ApiClient>().delete('/driver/empty-legs/${l.id}/');
      await _load();
    } on ApiException catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Return space')),
      floatingActionButton: FloatingActionButton.extended(onPressed: _new, icon: const Icon(Icons.add), label: const Text('Offer return space')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _legs == null && _error == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 96), children: [
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('Going back empty after a delivery? Tell us the route and date. Operations fills your truck or container with cargo going the same way, so you earn on the way back too.'),
                  ),
                ),
                if (_error != null) Padding(padding: const EdgeInsets.all(8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
                for (final l in _legs ?? <EmptyLeg>[])
                  // Grows with its content: a ListTile caps the height, and the
                  // chip + Withdraw button + up to four detail lines overflowed it.
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 12, 8),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Expanded(
                            child: Text('${l.originName} → ${l.destinationName}',
                                style: const TextStyle(fontWeight: FontWeight.w700, color: navy, fontSize: 15)),
                          ),
                          const SizedBox(width: 8),
                          StatusChip(status: l.status, label: l.statusDisplay),
                        ]),
                        const SizedBox(height: 6),
                        Text(
                          [
                            'From ${fmtDate(l.availableFrom)}${l.availableUntil != null ? ' to ${fmtDate(l.availableUntil)}' : ''}',
                            l.spaceDisplay,
                            if (l.truck != null) l.truck!.plate,
                            if (l.tripCode != null) 'Trip ${l.tripCode}',
                          ].join('\n'),
                          style: const TextStyle(color: Color(0xFF6B5B57), height: 1.35),
                        ),
                        if (l.status == 'open')
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton(onPressed: () => _withdraw(l), child: const Text('Withdraw')),
                          )
                        else
                          const SizedBox(height: 4),
                      ]),
                    ),
                  ),
                if ((_legs ?? []).isEmpty && _error == null)
                  const Padding(padding: EdgeInsets.all(24), child: Text('No offers yet.', textAlign: TextAlign.center)),
              ]),
      ),
    );
  }
}

class _EmptyLegForm extends StatefulWidget {
  const _EmptyLegForm();
  @override
  State<_EmptyLegForm> createState() => _EmptyLegFormState();
}

class _EmptyLegFormState extends State<_EmptyLegForm> {
  final _form = GlobalKey<FormState>();
  String? _origin, _destination;
  String _space = 'empty_truck';
  int? _truckId;
  DateTime _from = DateTime.now();
  DateTime? _until;
  final _vehicle = TextEditingController();
  final _kg = TextEditingController();
  final _notes = TextEditingController();
  List<TruckBrief> _trucks = [];
  bool _saving = false;
  ApiException? _err;

  @override
  void initState() {
    super.initState();
    context.read<ApiClient>().get('/driver/summary/').then((s) {
      if (!mounted) return;
      final trucks = (((s as Map)['trucks'] as List?) ?? []).map((e) => TruckBrief.fromJson(e as Map<String, dynamic>)).toList();
      setState(() {
        _trucks = trucks;
        if (trucks.length == 1) _truckId = trucks.first.id;
      });
    }).catchError((_) {});
  }

  @override
  void dispose() {
    _vehicle.dispose();
    _kg.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _pick(bool from) async {
    final now = DateTime.now();
    final d = await showDatePicker(
      context: context,
      initialDate: from ? _from : (_until ?? _from),
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 60)),
    );
    if (d != null) setState(() => from ? _from = d : _until = d);
  }

  String _iso(DateTime d) => d.toIso8601String().substring(0, 10);

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _saving = true; _err = null; });
    try {
      await context.read<ApiClient>().post('/driver/empty-legs/', body: {
        'origin': _origin,
        'destination': _destination,
        'available_from': _iso(_from),
        'available_until': _until == null ? null : _iso(_until!),
        'space': _space,
        'truck_id': _truckId,
        'vehicle_description': _vehicle.text.trim(),
        'capacity_kg': _kg.text.trim().isEmpty ? null : _kg.text.trim(),
        'notes': _notes.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() => _err = e);
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Offer return space')),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(padding: const EdgeInsets.all(16), children: [
            PlacePicker(label: 'Leaving from', value: _origin, required: true, errorText: _err?.field('origin'), onChanged: (v) => setState(() => _origin = v)),
            const SizedBox(height: 12),
            PlacePicker(label: 'Going to (your base)', value: _destination, required: true, errorText: _err?.field('destination'), onChanged: (v) => setState(() => _destination = v)),
            const SizedBox(height: 12),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.event_available_outlined),
              title: const Text('Available from'),
              subtitle: Text(fmtDate(_from)),
              trailing: TextButton(onPressed: () => _pick(true), child: const Text('Change')),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.event_busy_outlined),
              title: const Text('Can wait until (optional)'),
              subtitle: Text(_until == null ? 'Not set' : fmtDate(_until)),
              trailing: TextButton(onPressed: () => _pick(false), child: const Text('Choose')),
            ),
            if (_err?.field('available_until') != null) Text(_err!.field('available_until')!, style: const TextStyle(color: Colors.red)),
            DropdownButtonFormField<String>(
              initialValue: _space,
              decoration: const InputDecoration(labelText: 'Space'),
              items: [for (final e in spaceTypes.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
              onChanged: (v) => setState(() => _space = v!),
            ),
            const SizedBox(height: 12),
            if (_trucks.isNotEmpty)
              DropdownButtonFormField<int?>(
                initialValue: _truckId,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Truck'),
                items: [
                  const DropdownMenuItem(value: null, child: Text('Another truck')),
                  for (final t in _trucks)
                    DropdownMenuItem(value: t.id, child: Text('${t.plate} · ${t.typeDisplay}', overflow: TextOverflow.ellipsis)),
                ],
                onChanged: (v) => setState(() => _truckId = v),
              ),
            if (_truckId == null) ...[
              const SizedBox(height: 12),
              TextFormField(controller: _vehicle, maxLength: 120, decoration: const InputDecoration(labelText: 'Truck plate and type', hintText: 'e.g. UBK 123X, 40ft skeletal', counterText: '')),
            ],
            const SizedBox(height: 12),
            TextFormField(controller: _kg, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Load you can take (kg, optional)', errorText: _err?.field('capacity_kg'))),
            const SizedBox(height: 12),
            TextFormField(controller: _notes, maxLength: 500, maxLines: 3, decoration: const InputDecoration(labelText: 'Notes (optional)', hintText: 'e.g. Can load in Goma town or at the border', counterText: '')),
            const SizedBox(height: 16),
            FilledButton(onPressed: _saving ? null : _save, child: Text(_saving ? 'Sending…' : 'Send to operations')),
          ]),
        ),
      ),
    );
  }
}
