from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.core.testing import login_as
from apps.data.models import Shipment, ShipmentStatus, Trip

User = get_user_model()


class ShipmentTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.alice = User.objects.create_user("alice@example.com", "x-Strong-Pass-123", first_name="Alice", last_name="A")
        self.bob = User.objects.create_user("bob@example.com", "x-Strong-Pass-123", first_name="Bob", last_name="B")
        self.shipment = Shipment.objects.create(owner=self.alice, description="20 pairs of shoes", mode="part_load",
                                                origin="mombasa", destination="kampala")

    def test_tracking_number_format_and_initial_event(self):
        self.assertRegex(self.shipment.tracking_number, r"^XD[A-Z2-9]{10}$")
        self.assertEqual(self.shipment.events.count(), 1)

    def test_create_ignores_server_controlled_fields(self):
        login_as(self.client, self.alice)
        res = self.client.post("/api/shipments/", {
            "description": "Laptop accessories", "mode": "parcel", "origin": "nairobi", "destination": "kampala",
            "status": "delivered", "charge_usd": "0.01", "owner": str(self.bob.pk), "payment_status": "paid",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        s = Shipment.objects.get(tracking_number=res.data["tracking_number"])
        self.assertEqual(s.owner, self.alice)
        self.assertEqual(s.status, ShipmentStatus.BOOKED)
        self.assertIsNone(s.trip)
        self.assertIsNone(s.charge_usd)
        self.assertEqual(s.payment_status, "pending")

    def test_list_only_shows_own_shipments(self):
        Shipment.objects.create(owner=self.bob, description="Bob's goods", origin="kampala", destination="nairobi")
        login_as(self.client, self.alice)
        res = self.client.get("/api/shipments/")
        self.assertEqual(res.data["count"], 1)

    def test_filter_by_several_statuses(self):
        for st in ("in_transit", "at_border", "arrived"):
            Shipment.objects.create(owner=self.alice, description=st, mode="part_load", origin="kampala", destination="goma").update_status(st)
        login_as(self.client, self.alice)
        self.assertEqual(self.client.get("/api/shipments/", {"status": "in_transit,at_border"}).data["count"], 2)
        self.assertEqual(self.client.get("/api/shipments/", {"status": "booked"}).data["count"], 1)
        self.assertEqual(self.client.get("/api/shipments/", {"status": "arrived,bogus"}).status_code, 400)

    def test_other_users_shipment_is_404(self):
        login_as(self.client, self.bob)
        url = f"/api/shipments/{self.shipment.tracking_number}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"description": "hacked"}, format="json").status_code, 404)
        self.assertEqual(self.client.post(url + "cancel/").status_code, 404)

    def test_unauthenticated_denied(self):
        self.assertEqual(self.client.get("/api/shipments/").status_code, 401)

    def test_edit_locked_after_confirmation(self):
        self.shipment.update_status(ShipmentStatus.CONFIRMED)
        login_as(self.client, self.alice)
        res = self.client.patch(f"/api/shipments/{self.shipment.tracking_number}/", {"description": "changed"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cancel_unconfirmed_booking(self):
        login_as(self.client, self.alice)
        res = self.client.post(f"/api/shipments/{self.shipment.tracking_number}/cancel/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "cancelled")

    def test_delivery_requires_address(self):
        login_as(self.client, self.alice)
        res = self.client.post("/api/shipments/", {"description": "TV set", "origin": "kampala", "destination": "juba",
                                                  "delivery_option": "delivery"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_public_tracking_hides_private_fields(self):
        self.shipment.internal_notes = "secret"
        self.shipment.save()
        res = self.client.get(f"/api/track/{self.shipment.tracking_number.lower()}/")
        self.assertEqual(res.status_code, 200)
        body = str(res.data)
        for leaked in ("alice", "shoes", "secret", "charge", "owner", "note"):
            self.assertNotIn(leaked, body.lower())

    def test_public_tracking_invalid_format_404(self):
        self.assertEqual(self.client.get("/api/track/' OR 1=1--/").status_code, 404)

    def test_trip_status_propagates_to_shipments(self):
        trip = Trip.objects.create(origin="mombasa", destination="kampala")
        self.shipment.trip = trip
        self.shipment.save()
        moved = trip.advance("in_transit", place="malaba")
        self.assertEqual(moved, 1)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, ShipmentStatus.IN_TRANSIT)
        self.assertEqual(self.shipment.events.first().location, "Malaba border")

    def test_route_is_required_and_must_differ(self):
        login_as(self.client, self.alice)
        res = self.client.post("/api/shipments/", {"description": "Sugar bags"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("origin", res.data)
        res = self.client.post("/api/shipments/", {"description": "Sugar bags", "origin": "kampala", "destination": "kampala"}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.client.post("/api/shipments/", {"description": "Sugar bags", "origin": "kampala", "destination": "atlantis"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_legacy_wd_tracking_numbers_still_track(self):
        Shipment.objects.filter(pk=self.shipment.pk).update(tracking_number="WDABCDEFGHJK")
        self.assertEqual(self.client.get("/api/track/WDABCDEFGHJK/").status_code, 200)

    def test_summary(self):
        login_as(self.client, self.alice)
        res = self.client.get("/api/shipments/summary/")
        self.assertEqual(res.data["total"], 1)
        self.assertEqual(res.data["active"], 1)
