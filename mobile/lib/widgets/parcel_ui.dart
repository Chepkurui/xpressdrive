import 'package:flutter/material.dart';

import '../models/models.dart';
import 'common.dart';

// Analytics-style palette shared by the parcel screens: quiet greys for
// chrome, brand red for the one data series.
const kInk = Color(0xFF202124);
const kInk2 = Color(0xFF5F6368);
const kLine = Color(0xFFE3E5E8);
const kTrack = Color(0xFFEDEEF0);
const kSeries = Color(0xFF1D64C4);

class ParcelPanel extends StatelessWidget {
  const ParcelPanel({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: kLine, width: 2),
        ),
        child: child,
      );
}

/// Status colours are reserved for state and always sit next to the text label.
Color parcelStatusColor(String status) => switch (status) {
      'delivered' || 'arrived' => const Color(0xFF1F9D55),
      'cancelled' => const Color(0xFFB42318),
      'on_hold' => const Color(0xFFC27C0E),
      'booked' => const Color(0xFF9AA0A6),
      _ => const Color(0xFF1A73E8),
    };

class ParcelRow extends StatelessWidget {
  const ParcelRow({super.key, required this.shipment, required this.onTap});
  final Shipment shipment;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final s = shipment;
    final icon = switch (s.mode) {
      'parcel' => Icons.inventory_2_outlined,
      'container_20' || 'container_40' => Icons.view_in_ar_outlined,
      _ => Icons.local_shipping_outlined,
    };
    final step = statusSteps.indexOf(s.status);
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 12, 12),
        child: Row(children: [
          Container(
            width: 36, height: 36,
            decoration: const BoxDecoration(color: kTrack, shape: BoxShape.circle),
            child: Icon(icon, size: 18, color: kInk2),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(s.description, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: kInk)),
              const SizedBox(height: 2),
              Text('${s.part != null ? 'Part ${s.part!.number} of ${s.part!.count} · ' : ''}${s.trackingNumber} · ${s.route}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: kInk2, fontFamily: 'monospace')),
              const SizedBox(height: 8),
              Row(children: [
                Container(width: 8, height: 8, decoration: BoxDecoration(color: parcelStatusColor(s.status), shape: BoxShape.circle)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(s.statusDisplay, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: kInk)),
                ),
              ]),
              if (step >= 0) ...[
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(value: (step + 1) / statusSteps.length, minHeight: 3, color: progressColor((step + 1) / statusSteps.length), backgroundColor: kTrack),
                ),
              ],
            ]),
          ),
          const SizedBox(width: 12),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            const Text('ETA', style: TextStyle(fontSize: 11, color: kInk2)),
            Text(fmtDate(s.etaDate), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: kInk)),
            const SizedBox(height: 4),
            const Icon(Icons.chevron_right, size: 18, color: kInk2),
          ]),
        ]),
      ),
    );
  }
}

