import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/models.dart';
import '../theme.dart';

final _money = NumberFormat.currency(symbol: r'$', decimalDigits: 2);
String money(double? v) => v == null ? '—' : _money.format(v);
String fmtDate(DateTime? d) => d == null ? '—' : DateFormat('d MMM yyyy').format(d);
String fmtDateTime(DateTime? d) => d == null ? '—' : DateFormat('d MMM yyyy, HH:mm').format(d);

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status, required this.label});
  final String status, label;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (status) {
      'delivered' || 'arrived' || 'completed' || 'accepted' || 'open' => (const Color(0xFFE7F6ED), const Color(0xFF1F9D55)),
      'cancelled' || 'withdrawn' => (const Color(0xFFFDECEA), const Color(0xFFB42318)),
      'on_hold' || 'at_border' || 'allocated' => (const Color(0xFFFFF3E3), const Color(0xFFC27C0E)),
      'booked' || 'planned' || 'expired' => (const Color(0xFFE9EFF6), navy),
      _ => (const Color(0xFFEAF0FB), const Color(0xFF1D64C4)),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Text(label, style: TextStyle(color: fg, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}

/// Journey progress colour: red at the start, through orange and yellow,
/// to green on arrival. [fraction] is 0..1.
Color progressColor(double fraction) {
  final f = fraction.clamp(0.0, 1.0);
  return HSVColor.fromAHSV(1, 4 + 126 * f, 0.82, 0.78 - 0.1 * f).toColor();
}

class ProgressBarSteps extends StatelessWidget {
  const ProgressBarSteps({super.key, required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final i = statusSteps.indexOf(status);
    if (i < 0) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: LinearProgressIndicator(
          value: (i + 1) / statusSteps.length,
          minHeight: 8,
          backgroundColor: const Color(0xFFE0E6EE),
          color: progressColor((i + 1) / statusSteps.length),
        ),
      ),
      const SizedBox(height: 6),
      Text('Step ${i + 1} of ${statusSteps.length}', style: Theme.of(context).textTheme.bodySmall),
    ]);
  }
}

class Timeline extends StatelessWidget {
  const Timeline({super.key, required this.events});
  final List<TrackingEvent> events;

  @override
  Widget build(BuildContext context) {
    if (events.isEmpty) return const Text('No tracking events yet.');
    return Column(
      children: [
        for (var i = 0; i < events.length; i++)
          IntrinsicHeight(
            child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Column(children: [
                Container(
                  width: 14, height: 14, margin: const EdgeInsets.only(top: 4),
                  decoration: BoxDecoration(shape: BoxShape.circle, color: i == 0 ? amber : const Color(0xFFD5DEE8)),
                ),
                if (i < events.length - 1) Expanded(child: Container(width: 2, color: const Color(0xFFE0E6EE))),
              ]),
              const SizedBox(width: 12),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 18),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(events[i].statusDisplay, style: const TextStyle(fontWeight: FontWeight.w700)),
                    Text(fmtDateTime(events[i].createdAt), style: Theme.of(context).textTheme.bodySmall),
                    if (events[i].location.isNotEmpty) Text('📍 ${events[i].location}', style: Theme.of(context).textTheme.bodySmall),
                    if (events[i].note.isNotEmpty) Text(events[i].note),
                  ]),
                ),
              ),
            ]),
          ),
      ],
    );
  }
}

class InfoRow extends StatelessWidget {
  const InfoRow(this.label, this.value, {super.key});
  final String label, value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 140, child: Text(label, style: const TextStyle(color: Color(0xFF5B6878)))),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
        ]),
      );
}

void showError(BuildContext context, Object e) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()), backgroundColor: const Color(0xFFB42318)));
}
