import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../models/driver_models.dart';
import '../../state/location_service.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import '../../widgets/place_picker.dart';

/// One allocated trip: accept/decline, move it along, report checkpoints,
/// hand over cargo. The phone shares its position while the trip is live.
class DriverTripScreen extends StatefulWidget {
  const DriverTripScreen({super.key, required this.code});
  final String code;
  @override
  State<DriverTripScreen> createState() => _DriverTripScreenState();
}

class _DriverTripScreenState extends State<DriverTripScreen> {
  DriverTrip? _trip;
  String? _error;
  bool _busy = false;

  String get _url => '/driver/trips/${Uri.encodeComponent(widget.code)}/';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = DriverTrip.fromJson(await context.read<ApiClient>().get(_url) as Map<String, dynamic>);
      if (!mounted) return;
      setState(() { _trip = t; _error = null; });
      _syncSharing(t);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.status == 404 ? 'This trip is no longer allocated to you.' : e.message);
    }
  }

  void _syncSharing(DriverTrip t) {
    final loc = context.read<LocationService>();
    if (t.isLive) {
      loc.start(t.code);
    } else if (loc.tripCode == t.code) {
      loc.stop();
    }
  }

  /// Where the phone is now, attached to status changes and checkpoints for the ops log.
  Map<String, dynamic> _here() {
    final p = context.read<LocationService>().lastPosition;
    if (p == null) return {};
    return {'lat': double.parse(p.latitude.toStringAsFixed(6)), 'lng': double.parse(p.longitude.toStringAsFixed(6))};
  }

  Future<void> _post(String path, Map<String, dynamic> body, {String? ok}) async {
    setState(() => _busy = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final res = await context.read<ApiClient>().post('$_url$path', body: body);
      if (res is Map<String, dynamic> && res.containsKey('code')) {
        final t = DriverTrip.fromJson(res);
        setState(() => _trip = t);
        _syncSharing(t);
      }
      if (ok != null) messenger.showSnackBar(SnackBar(content: Text(ok)));
    } on ApiException catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _accept() async {
    // Ask for location before the trip starts, so sharing works from the first kilometre.
    await _post('respond/', {'accept': true}, ok: 'Trip accepted. Operations can now see your truck on their map.');
  }

  Future<void> _decline() async {
    final reason = TextEditingController();
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Decline this trip?'),
        content: TextField(controller: reason, maxLength: 255, decoration: const InputDecoration(labelText: 'Reason (optional)', hintText: 'e.g. Truck in the garage')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Keep it')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Decline')),
        ],
      ),
    );
    if (go != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<ApiClient>().post('${_url}respond/', body: {'accept': false, 'reason': reason.text.trim()});
      if (mounted) Navigator.pop(context);
    } on ApiException catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Status change or checkpoint, with an optional place and note.
  Future<void> _report({NextStatus? next}) async {
    final result = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _PlaceSheet(title: next?.label ?? 'Report a checkpoint', requirePlace: next == null),
    );
    if (result == null) return;
    final body = {...result, ..._here()};
    if (next != null) {
      await _post('status/', {...body, 'status': next.status}, ok: 'Updated: ${next.label}');
    } else {
      await _post('checkpoint/', body, ok: 'Checkpoint sent. Cargo owners have been updated.');
    }
  }

  Future<void> _delivered(Consignment c) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delivered ${c.trackingNumber}?'),
        content: Text('Confirm that ${c.description} was handed over to ${c.consigneeName.isEmpty ? 'the receiver' : c.consigneeName}.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Not yet')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delivered')),
        ],
      ),
    );
    if (ok == true) await _post('bookings/${Uri.encodeComponent(c.trackingNumber)}/delivered/', {}, ok: 'Marked as delivered.');
  }

  @override
  Widget build(BuildContext context) {
    final t = _trip;
    return Scaffold(
      appBar: AppBar(title: Text(t?.code ?? widget.code)),
      body: t == null
          ? Center(child: _error != null ? Padding(padding: const EdgeInsets.all(24), child: Text(_error!)) : const CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.all(12), children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Expanded(child: Text(t.route, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: navy))),
                        StatusChip(status: t.status, label: t.statusDisplay),
                      ]),
                      if (t.isBackhaul) const Padding(padding: EdgeInsets.only(top: 4), child: Text('Return leg: cargo on your way back to base', style: TextStyle(color: amberDark, fontWeight: FontWeight.w600))),
                      const SizedBox(height: 8),
                      InfoRow('Truck', t.truck == null ? 'Not set' : '${t.truck!.plate}${t.truck!.trailerPlate.isNotEmpty ? ' / ${t.truck!.trailerPlate}' : ''}'),
                      if (t.carrierReference.isNotEmpty) InfoRow('Container / ref', t.carrierReference),
                      InfoRow('Departure', fmtDate(t.departureDate)),
                      InfoRow('ETA', fmtDate(t.etaDate)),
                      InfoRow('Bookings', '${t.consignments.length}'),
                      if (t.notes.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text(t.notes)),
                    ]),
                  ),
                ),
                if (t.awaitingMyResponse)
                  Card(
                    color: const Color(0xFFFFF6EC),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        const Text('Operations has allocated this trip to you.', style: TextStyle(fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        const Text("If you accept, the app shares your truck's location with operations until the trip is complete. Cargo owners only see the towns and border posts you pass."),
                        const SizedBox(height: 12),
                        FilledButton.icon(onPressed: _busy ? null : _accept, icon: const Icon(Icons.check), label: const Text('Accept trip')),
                        const SizedBox(height: 8),
                        OutlinedButton(onPressed: _busy ? null : _decline, child: const Text('Decline')),
                      ]),
                    ),
                  ),
                if (t.nextStatuses.isNotEmpty || t.canReportCheckpoint)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                        Text('Update the trip', style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        for (final n in t.nextStatuses)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: FilledButton(onPressed: _busy ? null : () => _report(next: n), child: Text(_action(n))),
                          ),
                        if (t.canReportCheckpoint)
                          OutlinedButton.icon(
                            onPressed: _busy ? null : () => _report(),
                            icon: const Icon(Icons.place_outlined),
                            label: const Text('Report a checkpoint (town, weighbridge, border)'),
                          ),
                      ]),
                    ),
                  ),
                for (final c in t.consignments) _ConsignmentCard(c: c, canDeliver: const ['in_transit', 'at_border', 'arrived'].contains(t.status) && c.isOpen, busy: _busy, onDelivered: () => _delivered(c)),
                if (t.log.isNotEmpty)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Trip log', style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 8),
                        for (final e in t.log.take(15))
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Text('${fmtDateTime(e.at)} · ${e.kind == 'checkpoint' ? '📍 ${e.place}' : e.statusDisplay}${e.note.isNotEmpty ? '\n${e.note}' : ''}',
                                style: Theme.of(context).textTheme.bodySmall),
                          ),
                      ]),
                    ),
                  ),
              ]),
            ),
    );
  }

  String _action(NextStatus n) => switch (n.status) {
        'loading' => 'Start loading',
        'in_transit' => _trip?.status == 'at_border' ? 'Cleared the border, back on the road' : 'Depart: on the road',
        'at_border' => 'At a border / customs',
        'arrived' => 'Arrived at destination',
        'completed' => 'Complete trip',
        _ => n.label,
      };
}

class _ConsignmentCard extends StatelessWidget {
  const _ConsignmentCard({required this.c, required this.canDeliver, required this.busy, required this.onDelivered});
  final Consignment c;
  final bool canDeliver, busy;
  final VoidCallback onDelivered;

  @override
  Widget build(BuildContext context) {
    Widget phone(String label, String number) => number.isEmpty
        ? const SizedBox.shrink()
        : InkWell(
            onTap: () {
              Clipboard.setData(ClipboardData(text: number));
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$label number copied')));
            },
            child: Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Text('📞 $label: $number', style: const TextStyle(color: navy))),
          );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(c.trackingNumber, style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w700))),
            StatusChip(status: c.status, label: c.statusDisplay),
          ]),
          const SizedBox(height: 6),
          Text(c.description, style: const TextStyle(fontWeight: FontWeight.w600)),
          Text([
            c.modeDisplay,
            '${c.quantity} pkg',
            if (c.weightKg != null) '${c.weightKg!.toStringAsFixed(0)} kg',
            if (c.volumeCbm != null) '${c.volumeCbm} CBM',
          ].join(' · '), style: Theme.of(context).textTheme.bodySmall),
          if (c.isFragile || c.isHazardous)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text([if (c.isHazardous) '⚠️ Hazardous', if (c.isFragile) 'Fragile'].join(' · '), style: const TextStyle(color: Color(0xFFB42318), fontWeight: FontWeight.w600)),
            ),
          const Divider(height: 20),
          Text('Pick up: ${c.pickupAddress.isEmpty ? c.originName : c.pickupAddress}${c.pickupDate != null ? ' (${fmtDate(c.pickupDate)})' : ''}'),
          phone('Shipper ${c.shipper.name}', c.shipper.phone),
          const SizedBox(height: 6),
          Text('Deliver: ${c.deliveryAddress.isEmpty ? '${c.deliveryOptionDisplay}, ${c.destinationName}' : c.deliveryAddress}'),
          phone('Receiver${c.consigneeName.isEmpty ? '' : ' ${c.consigneeName}'}', c.consigneePhone),
          if (canDeliver) ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(onPressed: busy ? null : onDelivered, icon: const Icon(Icons.task_alt), label: const Text('Mark delivered')),
          ],
        ]),
      ),
    );
  }
}

/// Bottom sheet: where are you, and anything to add?
class _PlaceSheet extends StatefulWidget {
  const _PlaceSheet({required this.title, required this.requirePlace});
  final String title;
  final bool requirePlace;
  @override
  State<_PlaceSheet> createState() => _PlaceSheetState();
}

class _PlaceSheetState extends State<_PlaceSheet> {
  String? _place;
  final _label = TextEditingController();
  final _note = TextEditingController();

  @override
  void dispose() {
    _label.dispose();
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ready = !widget.requirePlace || _place != null || _label.text.trim().isNotEmpty;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(widget.title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 4),
        const Text('Cargo owners see the place name you choose, never your exact location.'),
        const SizedBox(height: 16),
        PlacePicker(label: widget.requirePlace ? 'Where are you?' : 'Where are you? (optional)', value: _place, borders: true, onChanged: (v) => setState(() => _place = v)),
        const SizedBox(height: 12),
        TextField(controller: _label, maxLength: 120, onChanged: (_) => setState(() {}), decoration: const InputDecoration(labelText: 'Or type the place', hintText: 'e.g. Lukaya weighbridge', counterText: '')),
        const SizedBox(height: 12),
        TextField(controller: _note, maxLength: 255, decoration: const InputDecoration(labelText: 'Note (optional)', hintText: 'e.g. Queue at the border, expect 6 hours', counterText: '')),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: ready ? () => Navigator.pop(context, {'place': _place ?? '', 'place_label': _label.text.trim(), 'note': _note.text.trim()}) : null,
          child: const Text('Send update'),
        ),
      ]),
    );
  }
}
