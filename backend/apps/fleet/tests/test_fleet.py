from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.scopes import CLIENT_MOBILE
from apps.core.testing import login_as
from apps.data.models import EmptyLeg, Shipment, ShipmentStatus, Trip, TripPosition, TripStatus, Truck

User = get_user_model()
PW = "x-Strong-Pass-123"


def staff(email, role):
    u = User.objects.create_user(email, PW, first_name="S", last_name=role, is_staff=True)
    u.groups.add(Group.objects.get(name=role))
    return User.objects.get(pk=u.pk)


class FleetBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user("owner@example.com", PW, first_name="Cargo", last_name="Owner")
        self.driver = User.objects.create_user("driver@example.com", PW, first_name="Dan", last_name="Driver", is_driver=True, phone="+256700111222")
        self.other_driver = User.objects.create_user("d2@example.com", PW, first_name="Eve", last_name="Other", is_driver=True)
        self.ops = staff("ops@example.com", "Operations")
        self.truck = Truck.objects.create(plate_number="ubk 412x", truck_type="container_40", capacity_kg=30000, default_driver=self.driver)
        self.trip = Trip.objects.create(origin="mombasa", destination="kampala", is_backhaul=True)
        self.booking = Shipment.objects.create(owner=self.owner, description="Cooking oil", origin="mombasa", destination="kampala",
                                               trip=self.trip, status=ShipmentStatus.CONFIRMED)

    def as_driver(self, user=None):
        login_as(self.client, user or self.driver, CLIENT_MOBILE)

    def allocate(self):
        login_as(self.client, self.ops)
        return self.client.post(f"/api/staff/trips/{self.trip.code}/allocate/",
                                {"driver": self.driver.customer_code, "truck_id": self.truck.pk}, format="json")


class DriverTokenTests(FleetBase):
    def test_mobile_driver_token_has_driver_scope_but_no_staff(self):
        res = self.client.post("/api/auth/login/", {"email": "driver@example.com", "password": PW}, format="json", HTTP_X_CLIENT="mobile")
        self.assertEqual(set(AccessToken(res.data["access"])["scope"].split()), {"account", "driver"})
        self.assertTrue(self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {res.data['access']}").data["is_driver"])

    def test_customers_and_staff_tokens_cannot_use_driver_api(self):
        login_as(self.client, self.owner, CLIENT_MOBILE)
        self.assertEqual(self.client.get("/api/driver/trips/").status_code, 403)
        login_as(self.client, self.ops)
        self.assertEqual(self.client.get("/api/driver/trips/").status_code, 403)
        self.assertEqual(self.client.get("/api/driver/trips/").status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/driver/summary/").status_code, 401)

    def test_driver_scope_is_dropped_when_driver_flag_removed(self):
        self.as_driver()
        User.objects.filter(pk=self.driver.pk).update(is_driver=False)
        self.assertEqual(self.client.get("/api/driver/trips/").status_code, 403)


class AllocationFlowTests(FleetBase):
    def test_allocate_accept_and_drive(self):
        res = self.allocate()
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "allocated")
        self.assertEqual(res.data["truck"]["plate_number"], "UBK 412X")

        self.as_driver()
        summary = self.client.get("/api/driver/summary/").data
        self.assertEqual(summary["pending_count"], 1)
        res = self.client.post(f"/api/driver/trips/{self.trip.code}/respond/", {"accept": True}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "accepted")
        self.assertEqual(res.data["next_statuses"][0]["status"], "loading")
        self.assertEqual(res.data["consignments"][0]["shipper"]["full_name"], "Cargo Owner")
        self.assertNotIn("charge_usd", res.data["consignments"][0])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, ShipmentStatus.ALLOCATED)

        # Skipping a stage is refused
        bad = self.client.post(f"/api/driver/trips/{self.trip.code}/status/", {"status": "arrived"}, format="json")
        self.assertEqual(bad.status_code, 400)
        for st, place in (("loading", "mombasa"), ("in_transit", ""), ("at_border", "malaba"), ("in_transit", "tororo"), ("arrived", "kampala")):
            res = self.client.post(f"/api/driver/trips/{self.trip.code}/status/", {"status": st, "place": place, "lat": 0.63, "lng": 34.28}, format="json")
            self.assertEqual(res.status_code, 200, (st, res.data))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, ShipmentStatus.ARRIVED)
        self.assertIn("Malaba border", list(self.booking.events.values_list("location", flat=True)))

        res = self.client.post(f"/api/driver/trips/{self.trip.code}/bookings/{self.booking.tracking_number}/delivered/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, ShipmentStatus.DELIVERED)
        res = self.client.post(f"/api/driver/trips/{self.trip.code}/status/", {"status": "completed"}, format="json")
        self.assertEqual(res.data["status"], "completed")

    def test_decline_returns_trip_to_planning(self):
        self.allocate()
        self.as_driver()
        res = self.client.post(f"/api/driver/trips/{self.trip.code}/respond/", {"accept": False, "reason": "Truck in garage"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.trip.refresh_from_db()
        self.assertEqual((self.trip.status, self.trip.driver, self.trip.driver_response), ("planned", None, "declined"))
        self.assertEqual(self.client.get(f"/api/driver/trips/{self.trip.code}/").status_code, 404)
        login_as(self.client, self.ops)
        self.assertEqual(self.client.get("/api/staff/summary/").data["trips"]["declined"], 1)

    def test_driver_sees_only_own_trips(self):
        self.allocate()
        self.as_driver(self.other_driver)
        self.assertEqual(self.client.get("/api/driver/trips/").data["count"], 0)
        self.assertEqual(self.client.get(f"/api/driver/trips/{self.trip.code}/").status_code, 404)
        res = self.client.post(f"/api/driver/trips/{self.trip.code}/positions/",
                               {"positions": [{"lat": 0.3, "lng": 32.5, "recorded_at": timezone.now().isoformat()}]}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_cannot_allocate_a_driver_already_on_the_road(self):
        busy = Trip.objects.create(origin="kampala", destination="goma", driver=self.driver, status=TripStatus.IN_TRANSIT)
        res = self.allocate()
        self.assertEqual(res.status_code, 400)
        self.assertIn(busy.code, str(res.data))


class PositionPrivacyTests(FleetBase):
    def start(self):
        self.allocate()
        self.as_driver()
        self.client.post(f"/api/driver/trips/{self.trip.code}/respond/", {"accept": True}, format="json")
        self.client.post(f"/api/driver/trips/{self.trip.code}/status/", {"status": "loading"}, format="json")
        self.client.post(f"/api/driver/trips/{self.trip.code}/status/", {"status": "in_transit"}, format="json")

    def send(self, *fixes):
        return self.client.post(f"/api/driver/trips/{self.trip.code}/positions/", {"positions": list(fixes)}, format="json")

    def test_positions_reach_staff_dashboard(self):
        self.start()
        now = timezone.now()
        res = self.send({"lat": 0.514123456, "lng": 35.27, "speed_kmh": 60, "recorded_at": (now - timedelta(minutes=1)).isoformat()},
                        {"lat": 0.52, "lng": 35.2, "speed_kmh": 62, "recorded_at": now.isoformat()})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["tracking"])
        login_as(self.client, self.ops)
        live = self.client.get("/api/staff/live/").data["trips"]
        self.assertEqual(live[0]["code"], self.trip.code)
        self.assertAlmostEqual(live[0]["last_position"]["lat"], 0.52)
        self.assertFalse(live[0]["stale"])
        trail = self.client.get(f"/api/staff/trips/{self.trip.code}/positions/").data
        self.assertEqual(trail["count"], 2)

    def test_positions_validated_and_refused_when_not_live(self):
        self.start()
        self.assertEqual(self.send({"lat": 95, "lng": 32, "recorded_at": timezone.now().isoformat()}).status_code, 400)
        future = (timezone.now() + timedelta(hours=2)).isoformat()
        self.assertEqual(self.send({"lat": 0.3, "lng": 32, "recorded_at": future}).status_code, 400)
        Trip.objects.filter(pk=self.trip.pk).update(status=TripStatus.COMPLETED)
        res = self.send({"lat": 0.3, "lng": 32, "recorded_at": timezone.now().isoformat()})
        self.assertFalse(res.data["tracking"])
        self.assertEqual(TripPosition.objects.count(), 0)

    def test_cargo_owner_sees_milestones_but_never_coordinates_or_driver(self):
        self.start()
        self.send({"lat": 0.514, "lng": 35.27, "recorded_at": timezone.now().isoformat()})
        self.client.post(f"/api/driver/trips/{self.trip.code}/checkpoint/", {"place": "eldoret", "lat": 0.514, "lng": 35.27}, format="json")
        login_as(self.client, self.owner)
        detail = self.client.get(f"/api/shipments/{self.booking.tracking_number}/").data
        self.assertEqual(detail["events"][0]["location"], "Eldoret")
        body = str(detail).lower()
        for leaked in ("0.514", "35.27", "lat", "lng", "dan", "driver", "ubk", self.trip.code.lower(), "position"):
            self.assertNotIn(leaked, body, leaked)
        public = str(self.client.get(f"/api/track/{self.booking.tracking_number}/").data).lower()
        for leaked in ("0.514", "lat", "driver", "ubk"):
            self.assertNotIn(leaked, public)
        # and customers cannot reach staff trip data
        self.assertEqual(self.client.get("/api/staff/live/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/staff/trips/{self.trip.code}/positions/").status_code, 403)

    def test_view_only_support_can_watch_but_not_move(self):
        self.start()
        support = staff("help@example.com", "Customer support")
        login_as(self.client, support)
        self.assertEqual(self.client.get("/api/staff/live/").status_code, 200)
        res = self.client.post(f"/api/staff/trips/{self.trip.code}/move/", {"status": "arrived"}, format="json")
        self.assertEqual(res.status_code, 403)


class EmptyLegTests(FleetBase):
    def offer(self, **kw):
        self.as_driver()
        body = {"origin": "kampala", "destination": "mombasa", "available_from": str(timezone.localdate() + timedelta(days=2)),
                "space": "empty_container_40", "truck_id": self.truck.pk, **kw}
        return self.client.post("/api/driver/empty-legs/", body, format="json")

    def test_driver_offers_and_ops_turns_it_into_an_allocated_backhaul_trip(self):
        res = self.offer(notes="Returning empty box to port")
        self.assertEqual(res.status_code, 201, res.data)
        leg_id = res.data["id"]
        # shows on the public board without identifying the driver or truck
        board = self.client.get("/api/capacity/").data
        self.assertEqual(board[0]["origin_name"], "Kampala")
        self.assertNotIn("UBK", str(board))
        self.assertNotIn("Dan", str(board))

        login_as(self.client, self.ops)
        res = self.client.post(f"/api/staff/empty-legs/{leg_id}/create-trip/", {}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["is_backhaul"])
        self.assertEqual(res.data["status"], "allocated")
        self.assertEqual(res.data["driver"]["customer_code"], self.driver.customer_code)
        self.assertEqual(EmptyLeg.objects.get(pk=leg_id).status, "matched")
        again = self.client.post(f"/api/staff/empty-legs/{leg_id}/create-trip/", {}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_validation_and_withdraw(self):
        self.assertEqual(self.offer(destination="kampala").status_code, 400)
        other_truck = Truck.objects.create(plate_number="KDA 1", default_driver=self.other_driver)
        self.assertEqual(self.offer(truck_id=other_truck.pk).status_code, 400)
        leg_id = self.offer().data["id"]
        self.as_driver(self.other_driver)
        self.assertEqual(self.client.delete(f"/api/driver/empty-legs/{leg_id}/").status_code, 404)
        self.as_driver()
        self.assertEqual(self.client.delete(f"/api/driver/empty-legs/{leg_id}/").status_code, 204)
        self.assertEqual(EmptyLeg.objects.get(pk=leg_id).status, "withdrawn")

    def test_places_are_public(self):
        places = {p["code"]: p for p in self.client.get("/api/places/").data}
        self.assertEqual(places["goma"]["country"], "DR Congo")
        self.assertEqual(places["malaba"]["kind"], "border")
