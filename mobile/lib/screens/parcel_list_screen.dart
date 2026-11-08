import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../widgets/parcel_ui.dart';
import 'shipment_detail_screen.dart';

final _trackingRe = RegExp(r'^(XD|WD)[A-Z0-9]{10}$');

/// A full, paginated list of the signed-in customer's own parcels: either all
/// of them, or the results of a tracking search from the Parcels tab.
///
/// Searches only ever cover the customer's parcels (the API is owner-scoped),
/// so a tracking number from someone else's account simply finds nothing.
class ParcelListScreen extends StatefulWidget {
  const ParcelListScreen({super.key, required this.title, this.search});

  const ParcelListScreen.search(String query, {super.key})
      : title = 'Tracking results',
        search = query;

  final String title;
  final String? search;

  @override
  State<ParcelListScreen> createState() => _ParcelListScreenState();
}

class _ParcelListScreenState extends State<ParcelListScreen> {
  final List<Shipment> _items = [];
  int _page = 1, _count = 0, _generation = 0;
  bool _hasMore = true, _loading = false, _loaded = false;
  String? _error;
  final _scroll = ScrollController();

  String get _upperSearch => (widget.search ?? '').toUpperCase();
  bool get _isTrackingNumber => _trackingRe.hasMatch(_upperSearch);

  @override
  void initState() {
    super.initState();
    _loadMore();
    _scroll.addListener(() {
      if (_scroll.position.pixels > _scroll.position.maxScrollExtent - 200) _loadMore();
    });
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    _generation++;
    setState(() {
      _items.clear();
      _page = 1;
      _hasMore = true;
      _loading = false;
      _loaded = false;
    });
    await _loadMore();
  }

  Future<void> _loadMore() async {
    if (_loading || !_hasMore) return;
    final gen = _generation;
    setState(() { _loading = true; _error = null; });
    try {
      final query = {if (widget.search != null) 'q': widget.search!, 'page': '$_page'};
      final data = await context.read<ApiClient>().get('/shipments/', query: query) as Map<String, dynamic>;
      if (!mounted || gen != _generation) return;
      final page = (data['results'] as List).map((e) => Shipment.fromJson(e as Map<String, dynamic>)).toList();
      _count = (data['count'] as num?)?.toInt() ?? 0;
      _hasMore = data['next'] != null;
      _page++;
      _items.addAll(page);
      _loaded = true;
      // An exact tracking number of one of their parcels goes straight to it.
      if (_isTrackingNumber && _page == 2 && _count == 1 && page.first.trackingNumber == _upperSearch) {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => ShipmentDetailScreen(trackingNumber: page.first.trackingNumber)));
        return;
      }
    } on ApiException catch (e) {
      if (gen == _generation) _error = e.message;
    } finally {
      if (mounted && gen == _generation) setState(() => _loading = false);
    }
  }

  Future<void> _open(Shipment s) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => ShipmentDetailScreen(trackingNumber: s.trackingNumber)));
    if (mounted) _reload();
  }

  @override
  Widget build(BuildContext context) {
    final searching = widget.search != null;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(2),
          child: SizedBox(height: 2, child: _loading && _items.isEmpty ? const LinearProgressIndicator(minHeight: 2) : null),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(controller: _scroll, padding: const EdgeInsets.fromLTRB(12, 12, 12, 32), children: [
          if (searching)
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 0, 4, 10),
              child: Text(
                _loaded ? '$_count result${_count == 1 ? '' : 's'} for “${widget.search}”' : 'Searching for “${widget.search}”…',
                style: const TextStyle(fontSize: 13, color: kInk2),
              ),
            ),
          if (_error != null)
            Padding(padding: const EdgeInsets.all(16), child: Text(_error!, style: const TextStyle(color: Color(0xFFB42318)))),
          if (_loaded && _items.isEmpty && _error == null)
            searching ? _NotFound(search: widget.search!, isTrackingNumber: _isTrackingNumber) : const _NoParcels()
          else if (_items.isNotEmpty)
            ParcelPanel(
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                for (var i = 0; i < _items.length; i++) ...[
                  if (i > 0) const Divider(height: 1, indent: 64, color: kLine),
                  ParcelRow(shipment: _items[i], onTap: () => _open(_items[i])),
                ],
                if (_loading)
                  const Padding(padding: EdgeInsets.all(16), child: Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5)))),
              ]),
            ),
        ]),
      ),
    );
  }
}

class _NoParcels extends StatelessWidget {
  const _NoParcels();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 48),
        child: Column(children: [
          Icon(Icons.inventory_2_outlined, size: 40, color: kInk2),
          SizedBox(height: 10),
          Text('You have no parcels yet', style: TextStyle(fontWeight: FontWeight.w600, color: kInk)),
        ]),
      );
}

/// Nothing on the customer's account matched. For a tracking number we say
/// plainly that only their own parcels can be tracked, without revealing
/// whether that number exists on someone else's account.
class _NotFound extends StatelessWidget {
  const _NotFound({required this.search, required this.isTrackingNumber});
  final String search;
  final bool isTrackingNumber;

  @override
  Widget build(BuildContext context) {
    if (!isTrackingNumber) {
      return const Padding(
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 48),
        child: Column(children: [
          Icon(Icons.search_off, size: 40, color: kInk2),
          SizedBox(height: 10),
          Text('None of your parcels match', style: TextStyle(fontWeight: FontWeight.w600, color: kInk)),
          SizedBox(height: 4),
          Text('Try a full tracking number (XD…) or a word from the description.', textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: kInk2)),
        ]),
      );
    }
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF3F2),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFECDCA), width: 1.5),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.lock_outline, color: Color(0xFFB42318)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text("You can't track this parcel", style: TextStyle(fontWeight: FontWeight.w700, color: Color(0xFFB42318))),
            const SizedBox(height: 6),
            Text(
              '${search.toUpperCase()} is not linked to your account. You can only track parcels on your own account. '
              'Check the number, or ask the person who sent it to share its tracking updates with you.',
              style: const TextStyle(fontSize: 13, color: kInk, height: 1.4),
            ),
          ]),
        ),
      ]),
    );
  }
}
