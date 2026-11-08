from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.core.testing import login_as
from apps.data.models import ContactMessage, Shipment, ShipmentStatus, ShippingRate, Trip

User = get_user_model()
PW = "x-Strong-Pass-123"


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label="data", codename__in=codenames))
    return User.objects.get(pk=user.pk)  # fresh instance: permission cache is per-object


class StaffAccessTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user("cust@example.com", PW, first_name="Cee", last_name="Customer")
        self.admin = User.objects.create_superuser("boss@example.com", PW, first_name="Boss", last_name="Admin")
        self.clerk = User.objects.create_user("clerk@example.com", PW, first_name="Clerk", last_name="Staff", is_staff=True)
        self.shipment = Shipment.objects.create(owner=self.customer, description="Shoes", mode="part_load", origin="mombasa", destination="kampala")

    def test_anonymous_and_customers_are_blocked_everywhere(self):
        urls = ["/api/staff/summary/", "/api/staff/shipments/", "/api/staff/users/", "/api/staff/rates/", "/api/staff/trips/", "/api/staff/live/", "/api/staff/trucks/", "/api/staff/empty-legs/", "/api/staff/messages/"]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 401, url)
        login_as(self.client, self.customer)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        res = self.client.post(f"/api/staff/shipments/{self.shipment.tracking_number}/status/", {"status": "delivered"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_staff_without_permissions_sees_nothing(self):
        login_as(self.client, self.clerk)
        self.assertEqual(self.client.get("/api/staff/shipments/").status_code, 403)
        self.assertEqual(self.client.get("/api/staff/summary/").data, {})

    def test_view_only_staff_cannot_change(self):
        clerk = grant(self.clerk, "view_shipment")
        login_as(self.client, clerk)
        self.assertEqual(self.client.get("/api/staff/shipments/").data["count"], 1)
        res = self.client.patch(f"/api/staff/shipments/{self.shipment.tracking_number}/", {"charge_usd": "10"}, format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.client.get("/api/staff/users/").status_code, 403)

    def test_me_reports_staff_access(self):
        login_as(self.client, grant(self.clerk, "view_shipment", "change_shipment"))
        access = self.client.get("/api/auth/me/").data["staff_access"]
        self.assertEqual(access["shipments"], {"view": True, "add": False, "change": True, "delete": False})
        self.assertEqual(access["users"], {"view": False, "add": False, "change": False, "delete": False})
        login_as(self.client, self.customer)
        me = self.client.get("/api/auth/me/").data
        self.assertFalse(me["is_staff"])
        self.assertIsNone(me["staff_access"])

    def test_customer_cannot_make_themselves_staff(self):
        login_as(self.client, self.customer)
        self.client.patch("/api/auth/me/", {"is_staff": True}, format="json")
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_staff)


class StaffShipmentTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user("cust@example.com", PW, first_name="Cee", last_name="Customer")
        self.admin = User.objects.create_superuser("boss@example.com", PW, first_name="Boss", last_name="Admin")
        self.s1 = Shipment.objects.create(owner=self.customer, description="Shoes", mode="part_load", origin="mombasa", destination="kampala")
        self.s2 = Shipment.objects.create(owner=self.customer, description="Phones", mode="parcel", origin="nairobi", destination="kampala")
        login_as(self.client, self.admin)

    def test_list_search_by_customer(self):
        res = self.client.get("/api/staff/shipments/", {"q": self.customer.customer_code})
        self.assertEqual(res.data["count"], 2)
        self.assertEqual(res.data["results"][0]["owner"]["email"], "cust@example.com")

    def test_dashboard_counts_match_their_stage_lists(self):
        # One booking per stage, plus a confirmed-but-unquoted and an unpaid one.
        for status in ("confirmed", "in_transit", "at_border", "arrived", "on_hold"):
            Shipment.objects.create(owner=self.customer, description=status, mode="part_load", origin="mombasa", destination="kampala").update_status(status)
        Shipment.objects.filter(description="arrived").update(payment_status="unpaid", charge_usd="40.00")
        summary = self.client.get("/api/staff/summary/").data["shipments"]
        pairs = {
            "booked": "booked", "awaiting_truck": "awaiting_truck", "transit": "in_transit", "arrived": "arrived",
            "on_hold": "on_hold", "awaiting_quote": "awaiting_quote", "unpaid": "unpaid_count", "no_trip": "no_trip",
        }
        for stage, key in pairs.items():
            listed = self.client.get("/api/staff/shipments/", {"stage": stage}).data["count"]
            self.assertEqual(listed, summary[key], stage)
        self.assertEqual(summary["booked"], 2)
        self.assertEqual(summary["in_transit"], 2)
        self.assertEqual(summary["no_trip"], 1)
        # New bookings are payment-pending too, but must not count as "needs a quote".
        self.assertEqual(summary["awaiting_quote"], 4)
        self.assertEqual(self.client.get("/api/staff/shipments/", {"stage": "nope"}).status_code, 400)

    def test_update_measurements_and_trip(self):
        trip = Trip.objects.create(origin="mombasa", destination="kampala")
        res = self.client.patch(f"/api/staff/shipments/{self.s1.tracking_number}/", {
            "weight_kg": "12.5", "volume_cbm": "0.4", "charge_usd": "70", "payment_status": "unpaid",
            "trip": trip.code, "internal_notes": "Box dented", "status": "delivered", "owner": "x",
        }, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.s1.refresh_from_db()
        self.assertEqual(self.s1.trip, trip)
        self.assertEqual(str(self.s1.charge_usd), "70.00")
        self.assertEqual(self.s1.status, ShipmentStatus.BOOKED)  # status only via /status/
        self.assertEqual(self.s1.owner, self.customer)

    def test_status_change_records_event(self):
        res = self.client.post(f"/api/staff/shipments/{self.s1.tracking_number}/status/",
                               {"status": "confirmed", "note": "2 pallets"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "confirmed")
        self.assertEqual(res.data["events"][0]["note"], "2 pallets")
        self.assertEqual(res.data["events"][0]["created_by_name"], "Boss Admin")
        self.assertEqual(res.data["events"][0]["location"], "Mombasa")

    def test_bulk_status(self):
        res = self.client.post("/api/staff/shipments/bulk-status/", {
            "tracking_numbers": [self.s1.tracking_number, self.s2.tracking_number], "status": "confirmed",
        }, format="json")
        self.assertEqual(res.data["updated"], 2)

    def test_trip_move_updates_bookings(self):
        res = self.client.post("/api/staff/trips/", {"origin": "mombasa", "destination": "kampala", "capacity_cbm": "67"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        code = res.data["code"]
        self.client.patch(f"/api/staff/shipments/{self.s1.tracking_number}/", {"trip": code, "volume_cbm": "1.5"}, format="json")
        self.assertEqual(str(self.client.get(f"/api/staff/trips/{code}/").data["used_cbm"]), "1.500")
        res = self.client.post(f"/api/staff/trips/{code}/move/", {"status": "in_transit", "place": "nairobi"}, format="json")
        self.assertEqual(res.data["moved"], 1)
        self.s1.refresh_from_db()
        self.assertEqual(self.s1.status, ShipmentStatus.IN_TRANSIT)
        self.assertEqual(self.s1.events.first().location, "Nairobi")
        bad = self.client.post(f"/api/staff/trips/{code}/move/", {"status": "teleported"}, format="json")
        self.assertEqual(bad.status_code, 400)
        # a truck that has left takes no more cargo
        late = self.client.patch(f"/api/staff/shipments/{self.s2.tracking_number}/", {"trip": code}, format="json")
        self.assertEqual(late.status_code, 400)

    def test_cancelling_a_trip_returns_cargo_to_the_queue(self):
        trip = Trip.objects.create(origin="mombasa", destination="kampala")
        Shipment.objects.filter(pk=self.s1.pk).update(trip=trip, status="confirmed")
        res = self.client.post(f"/api/staff/trips/{trip.code}/move/", {"status": "cancelled"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.s1.refresh_from_db()
        self.assertIsNone(self.s1.trip)


class StaffUserRateMessageTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user("cust@example.com", PW, first_name="Cee", last_name="Customer")
        self.admin = User.objects.create_superuser("boss@example.com", PW, first_name="Boss", last_name="Admin")
        self.clerk = grant(User.objects.create_user("clerk@example.com", PW, first_name="C", last_name="S", is_staff=True),
                           "view_user", "change_user")

    def test_edit_and_deactivate_customer(self):
        login_as(self.client, self.clerk)
        url = f"/api/staff/users/{self.customer.customer_code}/"
        res = self.client.patch(url, {"phone": "+256700000001", "is_active": False, "is_staff": True}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertFalse(self.customer.is_staff)  # cannot grant staff from the portal

    def test_non_superuser_cannot_edit_other_staff(self):
        login_as(self.client, self.clerk)
        res = self.client.patch(f"/api/staff/users/{self.admin.customer_code}/", {"first_name": "X"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_cannot_deactivate_self(self):
        login_as(self.client, self.admin)
        res = self.client.patch(f"/api/staff/users/{self.admin.customer_code}/", {"is_active": False}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_password_reset_email(self):
        login_as(self.client, self.clerk)
        res = self.client.post(f"/api/staff/users/{self.customer.customer_code}/password-reset/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password?uid=", mail.outbox[0].body)

    def test_rate_update_validates(self):
        rate = ShippingRate.objects.get(code="part-load")
        login_as(self.client, self.admin)
        res = self.client.patch(f"/api/staff/rates/{rate.code}/", {"price_usd": "360", "transit_days_min": 70}, format="json")
        self.assertEqual(res.status_code, 400)
        res = self.client.patch(f"/api/staff/rates/{rate.code}/", {"price_usd": "360"}, format="json")
        self.assertEqual(res.status_code, 200)
        rate.refresh_from_db()
        self.assertEqual(str(rate.price_usd), "360.00")

    def test_mark_message_handled(self):
        msg = ContactMessage.objects.create(name="A", email="a@example.com", subject="Hi", message="Hello")
        login_as(self.client, self.admin)
        self.assertEqual(self.client.get("/api/staff/messages/", {"handled": "false"}).data["count"], 1)
        res = self.client.patch(f"/api/staff/messages/{msg.pk}/", {"handled": True, "message": "changed"}, format="json")
        self.assertEqual(res.status_code, 200)
        msg.refresh_from_db()
        self.assertTrue(msg.handled)
        self.assertEqual(msg.message, "Hello")
