import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../models/driver_models.dart';
import '../../theme.dart';
import '../../widgets/common.dart';
import 'driver_trip_screen.dart';

/// Trips allocated to this driver: waiting for a reply, under way, finished.
class DriverTripsScreen extends StatefulWidget {
  const DriverTripsScreen({super.key, this.onChanged});
  final VoidCallback? onChanged;
  @override
  State<DriverTripsScreen> createState() => DriverTripsScreenState();
}

class DriverTripsScreenState extends State<DriverTripsScreen> {
  List<DriverTrip>? _current;
  List<DriverTrip>? _history;
  String? _error;

  @override
  void initState() {
    super.initState();
    reload();
  }

  Future<void> reload() async {
    final api = context.read<ApiClient>();
    try {
      final res = await Future.wait([
        api.get('/driver/trips/', query: {'state': 'active', 'page_size': '50'}),
        api.get('/driver/trips/', query: {'state': 'history', 'page_size': '20'}),
      ]);
      List<DriverTrip> parse(dynamic r) =>
          ((r as Map)['results'] as List).map((e) => DriverTrip.fromJson(e as Map<String, dynamic>)).toList();
      if (!mounted) return;
      setState(() {
        _current = parse(res[0]);
        _history = parse(res[1]);
        _error = null;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _open(DriverTrip t) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => DriverTripScreen(code: t.code)));
    await reload();
    widget.onChanged?.call();
  }

  @override
  Widget build(BuildContext context) {
    final waiting = _current?.where((t) => t.awaitingMyResponse).toList() ?? [];
    final rolling = _current?.where((t) => !t.awaitingMyResponse).toList() ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('My trips')),
      body: RefreshIndicator(
        onRefresh: reload,
        child: _current == null && _error == null
            ? const Center(child: CircularProgressIndicator())
            : ListView(padding: const EdgeInsets.all(12), children: [
                if (_error != null) Padding(padding: const EdgeInsets.all(8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
                if (waiting.isNotEmpty) ...[
                  const _Header('Waiting for your answer'),
                  for (final t in waiting) _TripCard(trip: t, highlight: true, onTap: () => _open(t)),
                ],
                const _Header('Current'),
                if (rolling.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(20),
                      child: Text('No trip right now. Operations will send new trips here. You can also offer return space under "Return space".'),
                    ),
                  ),
                for (final t in rolling) _TripCard(trip: t, onTap: () => _open(t)),
                if ((_history ?? []).isNotEmpty) ...[
                  const _Header('Finished'),
                  for (final t in _history!) _TripCard(trip: t, onTap: () => _open(t)),
                ],
              ]),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(4, 16, 4, 8),
        child: Text(text, style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700, color: navy)),
      );
}

class _TripCard extends StatelessWidget {
  const _TripCard({required this.trip, required this.onTap, this.highlight = false});
  final DriverTrip trip;
  final VoidCallback onTap;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Card(
      shape: highlight
          ? RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: amber, width: 2))
          : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text(trip.route, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: navy))),
              StatusChip(status: trip.status, label: trip.awaitingMyResponse ? 'New' : trip.statusDisplay),
            ]),
            const SizedBox(height: 6),
            Text([
              trip.code,
              if (trip.isBackhaul) 'Return leg',
              if (trip.truck != null) trip.truck!.plate,
              '${trip.shipmentCount} booking(s)',
            ].join(' · '), style: Theme.of(context).textTheme.bodySmall),
            if (trip.departureDate != null)
              Text('Departs ${fmtDate(trip.departureDate)}${trip.etaDate != null ? ' · ETA ${fmtDate(trip.etaDate)}' : ''}',
                  style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
      ),
    );
  }
}
