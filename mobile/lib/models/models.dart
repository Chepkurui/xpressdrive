double? _d(dynamic v) => v == null ? null : double.tryParse(v.toString());
DateTime? _dt(dynamic v) => v == null ? null : DateTime.tryParse(v.toString())?.toLocal();

class AppUser {
  AppUser.fromJson(Map<String, dynamic> j)
      : email = j['email'] ?? '',
        firstName = j['first_name'] ?? '',
        lastName = j['last_name'] ?? '',
        phone = j['phone'] ?? '',
        customerCode = j['customer_code'] ?? '',
        isDriver = j['is_driver'] == true,
        tokenScope = ((j['token_scope'] as List?) ?? []).cast<String>();
  final String email, firstName, lastName, phone, customerCode;
  final bool isDriver;
  final List<String> tokenScope;

  /// Driver features need the driver flag AND a token that carries the `driver` scope.
  bool get canDrive => isDriver && tokenScope.contains('driver');
}

class TrackingEvent {
  TrackingEvent.fromJson(Map<String, dynamic> j)
      : status = j['status'] ?? '',
        statusDisplay = statusLabel(j['status'], j['status_display']),
        location = j['location'] ?? '',
        note = j['note'] ?? '',
        createdAt = _dt(j['created_at']);
  final String status, statusDisplay, location, note;
  final DateTime? createdAt;
}

/// Set when a customer's cargo travels in several parts (split across trucks).
/// Parts always belong to the same customer.
class ShipmentPart {
  ShipmentPart.fromJson(Map<String, dynamic> j)
      : number = j['number'] ?? 1,
        count = j['count'] ?? 1,
        original = j['original'] ?? '',
        siblings = ((j['siblings'] as List?) ?? [])
            .map((e) => (
                  trackingNumber: (e['tracking_number'] ?? '') as String,
                  status: (e['status'] ?? '') as String,
                  statusDisplay: statusLabel(e['status'], e['status_display']),
                ))
            .toList();
  final int number, count;
  final String original;
  final List<({String trackingNumber, String status, String statusDisplay})> siblings;
}

class Shipment {
  Shipment.fromJson(Map<String, dynamic> j)
      : trackingNumber = j['tracking_number'] ?? '',
        description = j['description'] ?? '',
        category = j['category'] ?? 'general',
        categoryDisplay = j['category_display'] ?? '',
        mode = j['mode'] ?? '',
        modeDisplay = j['mode_display'] ?? '',
        serviceType = j['service_type'] ?? 'consolidated',
        serviceTypeDisplay = j['service_type_display'] ?? '',
        quantity = j['quantity'] ?? 1,
        status = j['status'] ?? '',
        statusDisplay = statusLabel(j['status'], j['status_display']),
        chargeUsd = _d(j['charge_usd']),
        paymentStatus = j['payment_status'] ?? '',
        paymentStatusDisplay = j['payment_status_display'] ?? '',
        etaDate = _dt(j['eta_date']),
        origin = j['origin'] ?? '',
        originName = j['origin_name'] ?? '',
        destination = j['destination'] ?? '',
        destinationName = j['destination_name'] ?? '',
        pickupAddress = j['pickup_address'] ?? '',
        pickupDate = _dt(j['pickup_date']),
        part = j['part'] == null ? null : ShipmentPart.fromJson(j['part'] as Map<String, dynamic>),
        createdAt = _dt(j['created_at']),
        consigneeName = j['consignee_name'] ?? '',
        consigneePhone = j['consignee_phone'] ?? '',
        declaredWeightKg = _d(j['declared_weight_kg']),
        declaredValueUsd = _d(j['declared_value_usd']),
        isHazardous = j['is_hazardous'] ?? false,
        isFragile = j['is_fragile'] ?? false,
        deliveryOption = j['delivery_option'] ?? 'pickup',
        deliveryOptionDisplay = j['delivery_option_display'] ?? '',
        deliveryAddress = j['delivery_address'] ?? '',
        customerNotes = j['customer_notes'] ?? '',
        weightKg = _d(j['weight_kg']),
        volumeCbm = _d(j['volume_cbm']),
        packagesReceived = j['packages_received'],
        isEditable = j['is_editable'] ?? false,
        events = ((j['events'] as List?) ?? [])
            .map((e) => TrackingEvent.fromJson(e as Map<String, dynamic>))
            .toList();

  final String trackingNumber, description, category, categoryDisplay, mode, modeDisplay, serviceType,
      serviceTypeDisplay, status, statusDisplay, paymentStatus, paymentStatusDisplay, consigneeName,
      consigneePhone, deliveryOption, deliveryOptionDisplay, deliveryAddress, customerNotes,
      origin, originName, destination, destinationName, pickupAddress;
  final int quantity;
  final int? packagesReceived;
  final double? chargeUsd, declaredValueUsd, declaredWeightKg, weightKg, volumeCbm;
  final DateTime? etaDate, createdAt, pickupDate;
  final ShipmentPart? part;
  final bool isHazardous, isFragile, isEditable;

  String get route => '$originName → $destinationName';
  final List<TrackingEvent> events;
}

class ShippingRate {
  ShippingRate.fromJson(Map<String, dynamic> j)
      : code = j['code'] ?? j['mode'],
        name = j['name'] ?? j['mode_display'],
        mode = j['mode'],
        modeDisplay = j['mode_display'],
        basis = j['basis'],
        priceUsd = _d(j['price_usd']) ?? 0,
        minChargeUsd = _d(j['min_charge_usd']) ?? 0,
        transitMin = j['transit_days_min'],
        transitMax = j['transit_days_max'],
        routeDisplay = j['route_display'] ?? '',
        summary = j['summary'] ?? '',
        bestFor = j['best_for'] ?? '';
  final String code, name, mode, modeDisplay, basis, summary, bestFor, routeDisplay;
  final double priceUsd, minChargeUsd;
  final int transitMin, transitMax;

  String get unit => switch (basis) { 'per_kg' => '/ kg', 'per_cbm' => '/ CBM', _ => '/ truck' };
}

/// Load types, from one parcel to a full container.
const shipmentModes = {
  'parcel': 'Parcel / small goods',
  'part_load': 'Part load (shared truck)',
  'full_truck': 'Full truck load',
  'container_20': '20ft container',
  'container_40': '40ft container',
};

const shipmentCategories = {
  'general': 'General goods',
  'fmcg': 'Food, drinks & FMCG',
  'agriculture': 'Agricultural produce',
  'electronics': 'Electronics & phones',
  'clothing': 'Clothing, shoes & bags',
  'home': 'Home, kitchen & furniture',
  'machinery': 'Machinery & spare parts',
  'building': 'Building & hardware',
  'other': 'Other',
};

const statusSteps = ['booked', 'confirmed', 'allocated', 'loaded', 'in_transit', 'at_border', 'arrived', 'delivered'];

String statusLabel(Object? status, Object? display) => display as String? ?? '';

/// Towns, ports and border posts served (from /api/places/).
class Place {
  Place.fromJson(Map<String, dynamic> j)
      : code = j['code'] ?? '',
        name = j['name'] ?? '',
        country = j['country'] ?? '',
        kind = j['kind'] ?? 'city';
  final String code, name, country, kind;
  bool get isBorder => kind == 'border';
}
