import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../widgets/common.dart';

class RatesScreen extends StatefulWidget {
  const RatesScreen({super.key});
  @override
  State<RatesScreen> createState() => _RatesScreenState();
}

class _RatesScreenState extends State<RatesScreen> {
  List<ShippingRate> _rates = [];
  String? _error;
  String? _plan; // pricing plan code; defaults once the rate card loads
  final _weight = TextEditingController();
  final _qty = TextEditingController(text: '1');
  final _l = TextEditingController(), _w = TextEditingController(), _h = TextEditingController();
  Map<String, dynamic>? _estimate;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in [_weight, _qty, _l, _w, _h]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await context.read<ApiClient>().get('/rates/', auth: false) as List;
      final rates = data.map((e) => ShippingRate.fromJson(e as Map<String, dynamic>)).toList();
      setState(() {
        _rates = rates;
        if (!rates.any((r) => r.code == _plan) && rates.isNotEmpty) {
          _plan = rates.firstWhere((r) => r.mode == 'part_load', orElse: () => rates.first).code;
        }
      });
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    }
  }

  Future<void> _calc() async {
    setState(() { _busy = true; _estimate = null; });
    final body = <String, dynamic>{
      if (_plan != null) 'plan': _plan else 'mode': 'part_load',
      'weight_kg': _weight.text.trim().isEmpty ? '1' : _weight.text.trim(),
      'quantity': int.tryParse(_qty.text) ?? 1,
      if (_l.text.isNotEmpty) 'length_cm': _l.text,
      if (_w.text.isNotEmpty) 'width_cm': _w.text,
      if (_h.text.isNotEmpty) 'height_cm': _h.text,
    };
    try {
      final data = await context.read<ApiClient>().post('/rates/estimate/', body: body, auth: false);
      setState(() => _estimate = data as Map<String, dynamic>);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _num(TextEditingController c, String label) => Expanded(
        child: TextField(controller: c, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: InputDecoration(labelText: label)),
      );

  @override
  Widget build(BuildContext context) {
    final est = _estimate;
    return Scaffold(
      appBar: AppBar(title: const Text('Rates & delivery times')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(12), children: [
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          for (final r in _rates)
            Card(
              child: ListTile(
                title: Text(r.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('${r.name != r.modeDisplay ? '${r.modeDisplay}\n' : ''}${r.routeDisplay.isNotEmpty ? '${r.routeDisplay}\n' : ''}${r.summary}\n⏱ ${r.transitMin}–${r.transitMax} days on the road'),
                isThreeLine: true,
                trailing: Text('from\n${money(r.priceUsd)}\n${r.unit}', textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w700)),
              ),
            ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Quick estimate', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: ValueKey(_plan),
                  initialValue: _plan,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Pricing plan'),
                  items: [for (final r in _rates) DropdownMenuItem(value: r.code, child: Text(r.name, overflow: TextOverflow.ellipsis))],
                  onChanged: (v) => setState(() => _plan = v),
                ),
                const SizedBox(height: 12),
                Row(children: [_num(_weight, 'Kg per package'), const SizedBox(width: 8), _num(_qty, 'Packages')]),
                const SizedBox(height: 12),
                Row(children: [_num(_l, 'L (cm)'), const SizedBox(width: 8), _num(_w, 'W (cm)'), const SizedBox(width: 8), _num(_h, 'H (cm)')]),
                const SizedBox(height: 12),
                FilledButton(onPressed: _busy ? null : _calc, child: Text(_busy ? 'Calculating…' : 'Estimate')),
                if (est != null) ...[
                  const SizedBox(height: 16),
                  Text('${money(double.tryParse(est['cost_low_usd']))} – ${money(double.tryParse(est['cost_high_usd']))}',
                      style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
                  Text('Chargeable: ${est['chargeable_quantity']} ${est['chargeable_unit']}'),
                  Text('Delivery: ${est['transit_days_min']}–${est['transit_days_max']} days after departure'),
                  const SizedBox(height: 8),
                  Text(est['disclaimer'] ?? '', style: Theme.of(context).textTheme.bodySmall),
                ],
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
