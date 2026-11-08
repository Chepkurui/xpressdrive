import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../widgets/common.dart';
import 'shipment_form_screen.dart';

class ShipmentDetailScreen extends StatefulWidget {
  const ShipmentDetailScreen({super.key, required this.trackingNumber});
  final String trackingNumber;
  @override
  State<ShipmentDetailScreen> createState() => _ShipmentDetailScreenState();
}

class _ShipmentDetailScreenState extends State<ShipmentDetailScreen> {
  Shipment? _s;
  String? _error;

  String get _path => '/shipments/${Uri.encodeComponent(widget.trackingNumber)}/';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await context.read<ApiClient>().get(_path);
      setState(() => _s = Shipment.fromJson(data as Map<String, dynamic>));
    } on ApiException catch (e) {
      setState(() => _error = e.status == 404 ? 'Parcel not found.' : e.message);
    }
  }

  Future<void> _cancel() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Cancel this request?'),
        content: const Text('This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Keep')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Cancel parcel')),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      final data = await context.read<ApiClient>().post('${_path}cancel/');
      setState(() => _s = Shipment.fromJson(data as Map<String, dynamic>));
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _s;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.trackingNumber),
        actions: [
          if (s != null && s.isEditable) ...[
            IconButton(
              tooltip: 'Edit',
              icon: const Icon(Icons.edit),
              onPressed: () async {
                final changed = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => ShipmentFormScreen(existing: s)));
                if (changed == true) _load();
              },
            ),
            IconButton(tooltip: 'Cancel', icon: const Icon(Icons.cancel_outlined), onPressed: _cancel),
          ],
        ],
      ),
      body: _error != null
          ? Center(child: Text(_error!))
          : s == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.all(12), children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Expanded(child: Text(s.description, style: Theme.of(context).textTheme.titleMedium)),
                            StatusChip(status: s.status, label: s.statusDisplay),
                          ]),
                          const SizedBox(height: 12),
                          ProgressBarSteps(status: s.status),
                        ]),
                      ),
                    ),
                    if (s.part != null) _PartsCard(part: s.part!),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Charges', style: Theme.of(context).textTheme.titleMedium),
                          InfoRow('Weight at loading', s.weightKg == null ? 'Pending' : '${s.weightKg} kg'),
                          if (s.volumeCbm != null) InfoRow('Volume', '${s.volumeCbm} CBM'),
                          InfoRow('Freight charge', money(s.chargeUsd)),
                          InfoRow('Payment', s.paymentStatusDisplay),
                          InfoRow('ETA ${s.destinationName}', fmtDate(s.etaDate)),
                        ]),
                      ),
                    ),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Milestones', style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 4),
                          Text("We post an update at each major town, weighbridge and border post. For security, the truck's live location isn't shared.",
                              style: Theme.of(context).textTheme.bodySmall),
                          const SizedBox(height: 12),
                          Timeline(events: s.events),
                        ]),
                      ),
                    ),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Details', style: Theme.of(context).textTheme.titleMedium),
                          InfoRow('Route', s.route),
                          InfoRow('Pickup', [s.pickupAddress, if (s.pickupDate != null) 'Ready ${fmtDate(s.pickupDate)}'].where((x) => x.isNotEmpty).join('\n').ifEmpty('—')),
                          InfoRow('Load type', s.modeDisplay),
                          InfoRow('Service', s.serviceTypeDisplay),
                          InfoRow('Category', s.categoryDisplay),
                          InfoRow('Quantity', '${s.quantity}'),
                          InfoRow('Declared weight', s.declaredWeightKg == null ? '—' : '${s.declaredWeightKg} kg'),
                          InfoRow('Cargo value', money(s.declaredValueUsd)),
                          InfoRow('Special handling', [if (s.isHazardous) 'Hazardous', if (s.isFragile) 'Fragile'].join(', ').ifEmpty('None')),
                          InfoRow('Receiver', [s.consigneeName, s.consigneePhone].where((x) => x.isNotEmpty).join('\n').ifEmpty('—')),
                          InfoRow('Delivery', s.deliveryOptionDisplay + (s.deliveryAddress.isEmpty ? '' : '\n${s.deliveryAddress}')),
                          InfoRow('Created', fmtDateTime(s.createdAt)),
                        ]),
                      ),
                    ),
                  ]),
                ),
    );
  }
}


/// "Part 2 of 3": the customer's cargo travels on several trucks.
class _PartsCard extends StatelessWidget {
  const _PartsCard({required this.part});
  final ShipmentPart part;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Part ${part.number} of ${part.count}', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Your goods travel in ${part.count} parts so they can ship as space allows.', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            for (final p in part.siblings)
              ListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                title: Text(p.trackingNumber, style: const TextStyle(fontFamily: 'monospace')),
                subtitle: p.trackingNumber == part.original ? const Text('Original') : null,
                trailing: StatusChip(status: p.status, label: p.statusDisplay),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => ShipmentDetailScreen(trackingNumber: p.trackingNumber)),
                ),
              ),
          ]),
        ),
      );
}

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}
