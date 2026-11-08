import 'package:flutter_test/flutter_test.dart';
import 'package:xpressdrive_mobile/api/api_client.dart';
import 'package:xpressdrive_mobile/models/driver_models.dart';
import 'package:xpressdrive_mobile/models/models.dart';

void main() {
  test('ApiException surfaces API detail message', () {
    expect(ApiException(400, {'detail': 'Nope'}).message, 'Nope');
    expect(ApiException(400, {'email': ['Taken']}).field('email'), 'Taken');
    expect(ApiException(0, null).message, contains('Network'));
  });

  test('Booking parses API payload with route and milestones', () {
    final s = Shipment.fromJson({
      'tracking_number': 'XDABCDEFGH23',
      'description': 'Cooking oil',
      'origin_name': 'Mombasa',
      'destination_name': 'Kampala',
      'status': 'in_transit',
      'status_display': 'In transit',
      'charge_usd': '12.50',
      'events': [
        {'status': 'in_transit', 'status_display': 'In transit', 'location': 'Malaba border', 'created_at': '2026-11-01T10:00:00Z'},
      ],
    });
    expect(s.chargeUsd, 12.5);
    expect(s.route, 'Mombasa → Kampala');
    expect(s.events.single.location, 'Malaba border');
  });

  test('Driver flag needs the driver token scope', () {
    expect(AppUser.fromJson({'is_driver': true, 'token_scope': ['account', 'driver']}).canDrive, isTrue);
    expect(AppUser.fromJson({'is_driver': true, 'token_scope': ['account']}).canDrive, isFalse);
    expect(AppUser.fromJson({'is_driver': false, 'token_scope': ['account', 'driver']}).canDrive, isFalse);
  });

  test('Driver trip parses allocation and next steps', () {
    final t = DriverTrip.fromJson({
      'code': 'XT2611ABCD',
      'status': 'allocated',
      'driver_response': 'pending',
      'origin_name': 'Kampala',
      'destination_name': 'Goma',
      'is_backhaul': true,
      'next_statuses': [],
      'consignments': [
        {'tracking_number': 'XD1', 'status': 'allocated', 'shipper': {'full_name': 'Sarah', 'phone': '+256700'}},
      ],
    });
    expect(t.awaitingMyResponse, isTrue);
    expect(t.route, 'Kampala → Goma');
    expect(t.consignments.single.shipper.name, 'Sarah');
    expect(t.consignments.single.isOpen, isTrue);
  });
}
