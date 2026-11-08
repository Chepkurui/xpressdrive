import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../models/models.dart';
import '../state/places.dart';

/// Dropdown of towns / ports (and optionally border posts), loaded from the API.
class PlacePicker extends StatefulWidget {
  const PlacePicker({super.key, required this.label, required this.value, required this.onChanged,
      this.borders = false, this.required = false, this.errorText});
  final String label;
  final String? value;
  final ValueChanged<String?> onChanged;
  final bool borders, required;
  final String? errorText;

  @override
  State<PlacePicker> createState() => _PlacePickerState();
}

class _PlacePickerState extends State<PlacePicker> {
  late final Future<List<Place>> _places = Places.load(context.read<ApiClient>());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Place>>(
      future: _places,
      builder: (context, snap) {
        final items = (snap.data ?? []).where((p) => widget.borders || !p.isBorder).toList();
        final value = items.any((p) => p.code == widget.value) ? widget.value : null;
        return DropdownButtonFormField<String>(
          initialValue: value,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: widget.label,
            errorText: widget.errorText,
            helperText: snap.hasError ? 'Could not load towns. Check your connection.' : null,
          ),
          items: [
            for (final p in items)
              DropdownMenuItem(value: p.code, child: Text('${p.name}  ·  ${p.country}', overflow: TextOverflow.ellipsis)),
          ],
          validator: widget.required ? (v) => v == null ? 'Required' : null : null,
          onChanged: widget.onChanged,
        );
      },
    );
  }
}
