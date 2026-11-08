import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../widgets/common.dart';
import '../widgets/place_picker.dart';

/// Book a truck: route, cargo (parcel → full container) and receiver.
class ShipmentFormScreen extends StatefulWidget {
  const ShipmentFormScreen({super.key, this.existing});
  final Shipment? existing;
  @override
  State<ShipmentFormScreen> createState() => _ShipmentFormScreenState();
}

class _ShipmentFormScreenState extends State<ShipmentFormScreen> {
  final _form = GlobalKey<FormState>();
  late final _description = TextEditingController(text: widget.existing?.description);
  late final _quantity = TextEditingController(text: '${widget.existing?.quantity ?? 1}');
  late final _weight = TextEditingController(text: widget.existing?.declaredWeightKg?.toString() ?? '');
  late final _value = TextEditingController(text: widget.existing?.declaredValueUsd?.toString() ?? '');
  late final _pickupAddress = TextEditingController(text: widget.existing?.pickupAddress);
  late final _consignee = TextEditingController(text: widget.existing?.consigneeName);
  late final _consigneePhone = TextEditingController(text: widget.existing?.consigneePhone);
  late final _address = TextEditingController(text: widget.existing?.deliveryAddress);
  late final _notes = TextEditingController(text: widget.existing?.customerNotes);
  late String? _origin = widget.existing?.origin;
  late String? _destination = widget.existing?.destination;
  late DateTime? _pickupDate = widget.existing?.pickupDate;
  late String _category = widget.existing?.category ?? 'general';
  late String _mode = widget.existing?.mode ?? 'part_load';
  late String _service = widget.existing?.serviceType ?? 'consolidated';
  late String _delivery = widget.existing?.deliveryOption ?? 'pickup';
  late bool _hazardous = widget.existing?.isHazardous ?? false;
  late bool _fragile = widget.existing?.isFragile ?? false;
  bool _saving = false;
  ApiException? _err;

  bool get _fullLoad => const ['full_truck', 'container_20', 'container_40'].contains(_mode);

  @override
  void dispose() {
    for (final c in [_description, _quantity, _weight, _value, _pickupAddress, _consignee, _consigneePhone, _address, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final d = await showDatePicker(
      context: context,
      initialDate: _pickupDate ?? now,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 180)),
    );
    if (d != null) setState(() => _pickupDate = d);
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _saving = true; _err = null; });
    String? opt(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();
    final body = {
      'origin': _origin,
      'destination': _destination,
      'pickup_address': _pickupAddress.text.trim(),
      'pickup_date': _pickupDate?.toIso8601String().substring(0, 10),
      'description': _description.text.trim(),
      'category': _category,
      'mode': _mode,
      'service_type': _fullLoad ? 'dedicated' : _service,
      'quantity': int.tryParse(_quantity.text) ?? 1,
      'declared_weight_kg': opt(_weight),
      'declared_value_usd': opt(_value),
      'is_hazardous': _hazardous,
      'is_fragile': _fragile,
      'consignee_name': _consignee.text.trim(),
      'consignee_phone': _consigneePhone.text.trim(),
      'delivery_option': _delivery,
      'delivery_address': _address.text.trim(),
      'customer_notes': _notes.text.trim(),
    };
    final api = context.read<ApiClient>();
    try {
      if (widget.existing == null) {
        await api.post('/shipments/', body: body);
      } else {
        await api.patch('/shipments/${Uri.encodeComponent(widget.existing!.trackingNumber)}/', body: body);
      }
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() => _err = e);
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Widget _dropdown(String label, String value, Map<String, String> items, ValueChanged<String> onChanged) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: DropdownButtonFormField<String>(
          initialValue: value,
          isExpanded: true,
          decoration: InputDecoration(labelText: label),
          items: [for (final e in items.entries) DropdownMenuItem(value: e.key, child: Text(e.value))],
          onChanged: (v) => setState(() => onChanged(v!)),
        ),
      );

  Widget _text(TextEditingController c, String label,
          {String? field, TextInputType? type, int maxLength = 255, int lines = 1, bool required = false, String? hint}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextFormField(
          controller: c,
          keyboardType: type,
          maxLength: maxLength,
          maxLines: lines,
          decoration: InputDecoration(labelText: label, hintText: hint, errorText: field == null ? null : _err?.field(field), counterText: ''),
          validator: required ? (v) => (v == null || v.trim().length < 3) ? 'Required' : null : null,
        ),
      );

  Widget _section(String title) => Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 12),
        child: Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.existing == null ? 'Book a truck' : 'Edit booking')),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(padding: const EdgeInsets.all(16), children: [
            const Text("Tell us what you're moving and where. We'll quote you and match it with a truck going your way, often one heading back to base."),
            const SizedBox(height: 8),
            _section('Route'),
            PlacePicker(label: 'From', value: _origin, required: true, errorText: _err?.field('origin'), onChanged: (v) => setState(() => _origin = v)),
            const SizedBox(height: 12),
            PlacePicker(label: 'To', value: _destination, required: true, errorText: _err?.field('destination'), onChanged: (v) => setState(() => _destination = v)),
            const SizedBox(height: 12),
            _text(_pickupAddress, 'Pickup address (warehouse, shop, port, ICD)'),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.event_outlined),
              title: const Text('Ready for pickup on'),
              subtitle: Text(_pickupDate == null ? 'Not set' : fmtDate(_pickupDate)),
              trailing: TextButton(onPressed: _pickDate, child: const Text('Choose')),
            ),
            _section('Cargo'),
            _dropdown('Load type', _mode, shipmentModes, (v) => _mode = v),
            _text(_description, 'What are you moving?', field: 'description', required: true, hint: 'e.g. 200 bags of maize flour, 25 kg each'),
            _dropdown('Category', _category, shipmentCategories, (v) => _category = v),
            Row(children: [
              Expanded(child: _text(_quantity, _fullLoad ? 'Trucks / containers' : 'Packages / pallets', field: 'quantity', type: TextInputType.number, maxLength: 5)),
              const SizedBox(width: 12),
              Expanded(child: _text(_weight, 'Total weight (kg)', field: 'declared_weight_kg', type: const TextInputType.numberWithOptions(decimal: true), maxLength: 10)),
            ]),
            _text(_value, 'Cargo value (USD)', field: 'declared_value_usd', type: const TextInputType.numberWithOptions(decimal: true), maxLength: 12),
            if (!_fullLoad)
              _dropdown('Service', _service, const {
                'consolidated': 'Shared truck (cheaper)',
                'dedicated': 'Dedicated truck (only my cargo)',
              }, (v) => _service = v),
            SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('Fragile'), value: _fragile, onChanged: (v) => setState(() => _fragile = v)),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Hazardous'),
              subtitle: const Text('Fuel, chemicals, gas, batteries'),
              value: _hazardous,
              onChanged: (v) => setState(() => _hazardous = v),
            ),
            _section('Receiver'),
            _text(_consignee, 'Receiver name', maxLength: 120),
            _text(_consigneePhone, 'Receiver phone', field: 'consignee_phone', type: TextInputType.phone, maxLength: 30),
            _dropdown('At the destination', _delivery, const {
              'pickup': 'Receiver collects from our depot',
              'delivery': "Deliver to the receiver's address",
            }, (v) => _delivery = v),
            if (_delivery == 'delivery') _text(_address, 'Delivery address', field: 'delivery_address', required: true),
            _text(_notes, 'Notes for our team', maxLength: 1000, lines: 3),
            FilledButton(onPressed: _saving ? null : _save, child: Text(_saving ? 'Saving…' : widget.existing == null ? 'Request booking' : 'Save')),
          ]),
        ),
      ),
    );
  }
}
