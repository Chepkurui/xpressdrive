import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/parcel_ui.dart';
import 'shipment_detail_screen.dart';
import 'shipment_form_screen.dart';
import 'parcel_list_screen.dart';


/// Headline numbers (display only; the pills below do the filtering).
const _scorecards = [('Active', 'active'), ('Arrived', 'arrived'), ('Delivered', 'delivered'), ('All', 'total')];

/// Active statuses grouped into the stages a customer cares about.
const _stages = [
  ('New bookings', Icons.edit_note_outlined, ['booked']),
  ('Awaiting truck', Icons.schedule_outlined, ['confirmed', 'allocated']),
  ('On the road', Icons.local_shipping_outlined, ['loaded', 'in_transit', 'at_border']),
  ('Arrived', Icons.flag_outlined, ['arrived']),
  ('On hold', Icons.pause_circle_outline, ['on_hold']),
];

/// A status pill above the list. [statuses] null means "use [query] as is".
class _Filter {
  const _Filter(this.key, this.label, {this.statuses, this.query = const {}, this.summaryKey});
  final String key, label;
  final List<String>? statuses;
  final Map<String, String> query;
  final String? summaryKey;

  Map<String, String> get params => statuses == null ? query : {'status': statuses!.join(',')};
}

const _filters = [
  _Filter('active', 'Active', query: {'state': 'active'}, summaryKey: 'active'),
  _Filter('new', 'New bookings', statuses: ['booked']),
  _Filter('waiting', 'Awaiting truck', statuses: ['confirmed', 'allocated']),
  _Filter('transit', 'On the road', statuses: ['loaded', 'in_transit', 'at_border']),
  _Filter('arrived', 'Arrived', statuses: ['arrived']),
  _Filter('on_hold', 'On hold', statuses: ['on_hold']),
  _Filter('delivered', 'Delivered', statuses: ['delivered']),
  _Filter('cancelled', 'Cancelled', statuses: ['cancelled']),
  _Filter('all', 'All', summaryKey: 'total'),
];

/// How many bookings the overview lists before "View all bookings".
const _previewSize = 10;

class ShipmentsScreen extends StatefulWidget {
  const ShipmentsScreen({super.key});
  @override
  State<ShipmentsScreen> createState() => _ShipmentsScreenState();
}

class _ShipmentsScreenState extends State<ShipmentsScreen> {
  _Filter _filter = _filters.first;
  final _search = TextEditingController();
  final List<Shipment> _items = [];
  Map<String, dynamic>? _summary;
  int _generation = 0; // discards responses that belong to a previous filter
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _reload({bool summary = true}) async {
    final gen = ++_generation;
    setState(() { _loading = true; _error = null; });
    final api = context.read<ApiClient>();
    try {
      final results = await Future.wait([
        api.get('/shipments/', query: {..._filter.params, 'page_size': '$_previewSize'}),
        if (summary) api.get('/shipments/summary/'),
      ]);
      if (!mounted || gen != _generation) return;
      final page = results[0] as Map<String, dynamic>;
      setState(() {
        _items
          ..clear()
          ..addAll((page['results'] as List).map((e) => Shipment.fromJson(e as Map<String, dynamic>)));
        if (summary) _summary = results[1] as Map<String, dynamic>;
      });
    } on ApiException catch (e) {
      if (mounted && gen == _generation) setState(() => _error = e.message);
    } finally {
      if (mounted && gen == _generation) setState(() => _loading = false);
    }
  }

  void _select(_Filter f) {
    if (f.key == _filter.key) return;
    setState(() => _filter = f);
    _reload(summary: false);
  }

  Future<void> _push(Widget screen) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => screen));
    if (mounted) _reload();
  }

  Future<void> _newRequest() async {
    final created = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const ShipmentFormScreen()));
    if (created == true) _reload();
  }

  void _runSearch(String v) {
    final q = v.trim();
    if (q.isEmpty) return;
    FocusScope.of(context).unfocus();
    _push(ParcelListScreen.search(q));
  }

  int _count(String key) => (_summary?[key] as num?)?.toInt() ?? 0;

  int _filterCount(_Filter f, Map<String, dynamic> byStatus) => f.summaryKey != null
      ? _count(f.summaryKey!)
      : f.statuses!.fold<int>(0, (n, k) => n + ((byStatus[k] as num?)?.toInt() ?? 0));

  @override
  Widget build(BuildContext context) {
    final byStatus = (_summary?['by_status'] as Map?)?.cast<String, dynamic>() ?? const {};
    final stageCounts = [
      for (final s in _stages) s.$3.fold<int>(0, (n, k) => n + ((byStatus[k] as num?)?.toInt() ?? 0)),
    ];
    final charges = double.tryParse('${_summary?['total_charges_usd'] ?? ''}');
    final shown = _summary == null ? null : _filterCount(_filter, byStatus);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Bookings'),
        actions: [IconButton(tooltip: 'Refresh', onPressed: _reload, icon: const Icon(Icons.refresh))],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(66),
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
              child: TextField(
                controller: _search,
                textInputAction: TextInputAction.search,
                maxLength: 60,
                onSubmitted: _runSearch,
                decoration: InputDecoration(
                  counterText: '',
                  isDense: true,
                  hintText: 'Find a booking: tracking no. or description',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: ListenableBuilder(
                    listenable: _search,
                    builder: (_, _) => _search.text.trim().isEmpty
                        ? const SizedBox.shrink()
                        : IconButton(tooltip: 'Search', icon: const Icon(Icons.arrow_forward), onPressed: () => _runSearch(_search.text)),
                  ),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
                ),
              ),
            ),
            SizedBox(
              height: 2,
              child: _loading ? const LinearProgressIndicator(minHeight: 2, color: amber, backgroundColor: Colors.transparent) : null,
            ),
          ]),
        ),
      ),
      body: RefreshIndicator(
        color: kSeries,
        onRefresh: _reload,
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
          ParcelPanel(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              _Scorecards(count: _count),
              const Divider(height: 1, color: kLine),
              _StageBreakdown(counts: stageCounts),
            ]),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _MiniStat(icon: Icons.receipt_long_outlined, label: 'Total charges', value: _summary == null ? '—' : money(charges ?? 0))),
            const SizedBox(width: 12),
            Expanded(
              child: _MiniStat(
                icon: Icons.error_outline,
                label: 'Awaiting payment',
                value: _summary == null ? '—' : '${_count('awaiting_payment')}',
                attention: _count('awaiting_payment') > 0,
              ),
            ),
          ]),
          const SizedBox(height: 12),
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Flexible(
              child: _FilterDropdown(
                filters: _filters,
                selected: _filter,
                count: (f) => _summary == null ? null : _filterCount(f, byStatus),
                onSelect: _select,
              ),
            ),
            const SizedBox(width: 12),
            FilledButton.icon(
              style: FilledButton.styleFrom(minimumSize: const Size(0, 44), padding: const EdgeInsets.symmetric(horizontal: 16)),
              onPressed: _newRequest,
              icon: const Icon(Icons.add, size: 20),
              label: const Text('Book a truck'),
            ),
          ]),
          const SizedBox(height: 12),
          ParcelPanel(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
                child: Row(children: [
                  Expanded(child: Text('${_filter.label} bookings', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: kInk))),
                  if (shown != null) Text(shown > _items.length ? 'Latest ${_items.length} of $shown' : '$shown total', style: const TextStyle(fontSize: 12, color: kInk2)),
                ]),
              ),
              const Divider(height: 1, color: kLine),
              if (_error != null)
                Padding(padding: const EdgeInsets.all(16), child: Text(_error!, style: const TextStyle(color: Color(0xFFB42318)))),
              if (!_loading && _items.isEmpty && _error == null) _EmptyState(filtered: _filter.key != 'active' && _filter.key != 'all'),
              for (var i = 0; i < _items.length; i++) ...[
                if (i > 0) const Divider(height: 1, indent: 64, color: kLine),
                ParcelRow(shipment: _items[i], onTap: () => _push(ShipmentDetailScreen(trackingNumber: _items[i].trackingNumber))),
              ],
            ]),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(46), backgroundColor: Colors.white, side: const BorderSide(color: kLine, width: 2)),
            onPressed: () => _push(const ParcelListScreen(title: 'All bookings')),
            icon: const Icon(Icons.list_alt_outlined),
            label: Text(_summary == null ? 'View all bookings' : 'View all bookings (${_count('total')})'),
          ),
        ]),
      ),
    );
  }
}


class _Scorecards extends StatelessWidget {
  const _Scorecards({required this.count});
  final int Function(String) count;

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        for (var i = 0; i < _scorecards.length; i++) ...[
          if (i > 0) const VerticalDivider(width: 1, color: kLine),
          Expanded(child: _scorecard(_scorecards[i].$1, count(_scorecards[i].$2))),
        ],
      ]),
    );
  }

  Widget _scorecard(String label, int n) => Semantics(
        label: '$label: $n',
        excludeSemantics: true,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 8, 14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: n.toDouble()),
              duration: const Duration(milliseconds: 700),
              curve: Curves.easeOutCubic,
              builder: (_, v, _) => Text(
                '${v.round()}',
                style: const TextStyle(fontSize: 24, height: 1.1, fontWeight: FontWeight.w500, color: kInk, fontFeatures: [FontFeature.tabularFigures()]),
              ),
            ),
            const SizedBox(height: 4),
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: kInk2, fontWeight: FontWeight.w500)),
          ]),
        ),
      );
}

/// Status filter as a compact dropdown; each option shows its booking count.
class _FilterDropdown extends StatelessWidget {
  const _FilterDropdown({required this.filters, required this.selected, required this.count, required this.onSelect});
  final List<_Filter> filters;
  final _Filter selected;
  final int? Function(_Filter) count;
  final ValueChanged<_Filter> onSelect;

  Widget _badge(int? n, {bool strong = false}) => n == null
      ? const SizedBox.shrink()
      : Container(
          margin: const EdgeInsets.only(left: 8),
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
          decoration: BoxDecoration(color: strong ? amber : kTrack, borderRadius: BorderRadius.circular(999)),
          child: Text('$n', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: strong ? navy : kInk2)),
        );

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 44,
      padding: const EdgeInsets.only(left: 12, right: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: kLine, width: 2),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: selected.key,
          isDense: true,
          borderRadius: BorderRadius.circular(12),
          dropdownColor: Colors.white,
          icon: const Icon(Icons.expand_more, color: kInk2),
          onChanged: (k) => onSelect(filters.firstWhere((f) => f.key == k)),
          // The closed button: filter icon, current label and its count.
          selectedItemBuilder: (_) => [
            for (final f in filters)
              Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.filter_list, size: 18, color: navy),
                const SizedBox(width: 8),
                Flexible(child: Text(f.label, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: kInk))),
                _badge(count(f), strong: true),
              ]),
          ],
          items: [
            for (final f in filters)
              DropdownMenuItem(
                value: f.key,
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(f.label, style: TextStyle(fontSize: 14, fontWeight: f.key == selected.key ? FontWeight.w700 : FontWeight.w500, color: f.key == selected.key ? navy : kInk)),
                  _badge(count(f)),
                ]),
              ),
          ],
        ),
      ),
    );
  }
}

/// "Where is my cargo?": active bookings per stage, with count and share.
class _StageBreakdown extends StatelessWidget {
  const _StageBreakdown({required this.counts});
  final List<int> counts;

  @override
  Widget build(BuildContext context) {
    final total = counts.fold<int>(0, (a, b) => a + b);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Row(children: [
          Expanded(child: Text('Active bookings by stage', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: kInk))),
          Text('Bookings', style: TextStyle(fontSize: 11, color: kInk2)),
        ]),
        const SizedBox(height: 10),
        for (var i = 0; i < _stages.length; i++)
          _StageRow(
            icon: _stages[i].$2,
            label: _stages[i].$1,
            value: counts[i],
            share: total == 0 ? 0 : counts[i] / total,
          ),
      ]),
    );
  }
}

class _StageRow extends StatelessWidget {
  const _StageRow({required this.icon, required this.label, required this.value, required this.share});
  final IconData icon;
  final String label;
  final int value;
  final double share;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label: $value, ${(share * 100).round()} percent',
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Icon(icon, size: 16, color: kInk2),
            const SizedBox(width: 8),
            Expanded(child: Text(label, style: const TextStyle(fontSize: 13, color: kInk))),
            Text('$value', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: kInk, fontFeatures: [FontFeature.tabularFigures()])),
            SizedBox(
              width: 44,
              child: Text('${(share * 100).round()}%', textAlign: TextAlign.right, style: const TextStyle(fontSize: 12, color: kInk2, fontFeatures: [FontFeature.tabularFigures()])),
            ),
          ]),
        ]),
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({required this.icon, required this.label, required this.value, this.attention = false});
  final IconData icon;
  final String label, value;
  final bool attention;

  @override
  Widget build(BuildContext context) {
    final accent = attention ? const Color(0xFFB54708) : kInk2;
    return ParcelPanel(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(color: attention ? const Color(0xFFFEF0C7) : kTrack, borderRadius: BorderRadius.circular(8)),
            child: Icon(icon, size: 20, color: accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: kInk2)),
              const SizedBox(height: 2),
              Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: kInk)),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({this.filtered = false});
  final bool filtered;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 36),
        child: Column(children: [
          const Icon(Icons.inventory_2_outlined, size: 40, color: kInk2),
          const SizedBox(height: 10),
          Text(filtered ? 'No bookings in this status' : 'No bookings here yet', style: const TextStyle(fontWeight: FontWeight.w600, color: kInk)),
          if (!filtered) ...[
            const SizedBox(height: 4),
            const Text('Tap "Book a truck" to move anything from a parcel to a full container.', textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: kInk2)),
          ],
        ]),
      );
}
