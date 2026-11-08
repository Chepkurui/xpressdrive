// Models for the driver side of the app (/api/driver/...).

double? _d(dynamic v) => v == null ? null : double.tryParse(v.toString());
DateTime? _dt(dynamic v) => v == null ? null : DateTime.tryParse(v.toString())?.toLocal();
List<Map<String, dynamic>> _list(dynamic v) => ((v as List?) ?? []).cast<Map<String, dynamic>>();

class TruckBrief {
  TruckBrief.fromJson(Map<String, dynamic> j)
      : id = j['id'] ?? 0,
        plate = j['plate_number'] ?? '',
        trailerPlate = j['trailer_plate'] ?? '',
        typeDisplay = j['truck_type_display'] ?? '';
  final int id;
  final String plate, trailerPlate, typeDisplay;
}

class NextStatus {
  NextStatus.fromJson(Map<String, dynamic> j)
      : status = j['status'] ?? '',
        label = j['label'] ?? '';
  final String status, label;
}

class Person {
  Person.fromJson(Map<String, dynamic>? j)
      : name = j?['full_name'] ?? '',
        phone = j?['phone'] ?? '';
  final String name, phone;
}

class Consignment {
  Consignment.fromJson(Map<String, dynamic> j)
      : trackingNumber = j['tracking_number'] ?? '',
        description = j['description'] ?? '',
        modeDisplay = j['mode_display'] ?? '',
        quantity = j['quantity'] ?? 1,
        weightKg = _d(j['weight_kg']) ?? _d(j['declared_weight_kg']),
        volumeCbm = _d(j['volume_cbm']),
        isFragile = j['is_fragile'] == true,
        isHazardous = j['is_hazardous'] == true,
        status = j['status'] ?? '',
        statusDisplay = j['status_display'] ?? '',
        originName = j['origin_name'] ?? '',
        destinationName = j['destination_name'] ?? '',
        pickupAddress = j['pickup_address'] ?? '',
        pickupDate = _dt(j['pickup_date']),
        shipper = Person.fromJson(j['shipper'] as Map<String, dynamic>?),
        consigneeName = j['consignee_name'] ?? '',
        consigneePhone = j['consignee_phone'] ?? '',
        deliveryOptionDisplay = j['delivery_option_display'] ?? '',
        deliveryAddress = j['delivery_address'] ?? '';
  final String trackingNumber, description, modeDisplay, status, statusDisplay, originName, destinationName,
      pickupAddress, consigneeName, consigneePhone, deliveryOptionDisplay, deliveryAddress;
  final int quantity;
  final double? weightKg, volumeCbm;
  final bool isFragile, isHazardous;
  final DateTime? pickupDate;
  final Person shipper;
  bool get isOpen => status != 'delivered' && status != 'cancelled';
}

class TripLogEntry {
  TripLogEntry.fromJson(Map<String, dynamic> j)
      : kind = j['kind'] ?? '',
        statusDisplay = j['status_display'] ?? '',
        place = j['place_label'] ?? '',
        note = j['note'] ?? '',
        at = _dt(j['created_at']);
  final String kind, statusDisplay, place, note;
  final DateTime? at;
}

class DriverTrip {
  DriverTrip.fromJson(Map<String, dynamic> j)
      : code = j['code'] ?? '',
        status = j['status'] ?? '',
        statusDisplay = j['status_display'] ?? '',
        origin = j['origin'] ?? '',
        originName = j['origin_name'] ?? '',
        destination = j['destination'] ?? '',
        destinationName = j['destination_name'] ?? '',
        isBackhaul = j['is_backhaul'] == true,
        truck = j['truck'] == null ? null : TruckBrief.fromJson(j['truck'] as Map<String, dynamic>),
        driverResponse = j['driver_response'] ?? '',
        carrierReference = j['carrier_reference'] ?? '',
        departureDate = _dt(j['departure_date']),
        etaDate = _dt(j['eta_date']),
        notes = j['notes'] ?? '',
        allocatedAt = _dt(j['allocated_at']),
        shipmentCount = j['shipment_count'] ?? 0,
        nextStatuses = _list(j['next_statuses']).map(NextStatus.fromJson).toList(),
        isLive = j['is_live'] == true,
        lastPositionAt = _dt((j['last_position'] as Map?)?['at']),
        consignments = _list(j['consignments']).map(Consignment.fromJson).toList(),
        log = _list(j['events']).map(TripLogEntry.fromJson).toList();

  final String code, status, statusDisplay, origin, originName, destination, destinationName, driverResponse,
      carrierReference, notes;
  final bool isBackhaul, isLive;
  final TruckBrief? truck;
  final DateTime? departureDate, etaDate, allocatedAt, lastPositionAt;
  final int shipmentCount;
  final List<NextStatus> nextStatuses;
  final List<Consignment> consignments;
  final List<TripLogEntry> log;

  bool get awaitingMyResponse => status == 'allocated' && driverResponse == 'pending';
  bool get isFinished => status == 'completed' || status == 'cancelled';
  bool get canReportCheckpoint => const ['loading', 'in_transit', 'at_border', 'arrived'].contains(status);
  String get route => '$originName → $destinationName';
}

class EmptyLeg {
  EmptyLeg.fromJson(Map<String, dynamic> j)
      : id = j['id'] ?? 0,
        origin = j['origin'] ?? '',
        originName = j['origin_name'] ?? '',
        destination = j['destination'] ?? '',
        destinationName = j['destination_name'] ?? '',
        availableFrom = _dt(j['available_from']),
        availableUntil = _dt(j['available_until']),
        space = j['space'] ?? '',
        spaceDisplay = j['space_display'] ?? '',
        status = j['status'] ?? '',
        statusDisplay = j['status_display'] ?? '',
        notes = j['notes'] ?? '',
        tripCode = j['trip_code'],
        truck = j['truck'] == null ? null : TruckBrief.fromJson(j['truck'] as Map<String, dynamic>);
  final int id;
  final String origin, originName, destination, destinationName, space, spaceDisplay, status, statusDisplay, notes;
  final String? tripCode;
  final DateTime? availableFrom, availableUntil;
  final TruckBrief? truck;
}

const spaceTypes = {
  'empty_truck': 'Empty truck',
  'empty_container_20': 'Empty 20ft container',
  'empty_container_40': 'Empty 40ft container',
  'partial': 'Part space available',
};
