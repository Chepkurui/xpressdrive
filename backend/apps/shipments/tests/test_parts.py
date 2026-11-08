from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.core.testing import login_as
from apps.data.models import Shipment, ShipmentStatus, Trip

User = get_user_model()
PW = "x-Strong-Pass-123"


class SplitAndPrivacyTests(APITestCase):
    """One trip carries many customers' cargo; one customer's cargo can be split
    across trucks; customers never see each other's cargo."""

    def setUp(self):
        cache.clear()
        self.alice = User.objects.create_user("alice@example.com", PW, first_name="Alice", last_name="A")
        self.bob = User.objects.create_user("bob@example.com", PW, first_name="Bob", last_name="B")
        self.ops = User.objects.create_user("ops@example.com", PW, first_name="O", last_name="P", is_staff=True)
        self.ops.groups.add(Group.objects.get(name="Operations"))
        self.ops = User.objects.get(pk=self.ops.pk)

        self.flight1 = Trip.objects.create(origin="mombasa", destination="kampala")
        self.flight2 = Trip.objects.create(origin="mombasa", destination="kampala", is_backhaul=True)
        self.alice_goods = Shipment.objects.create(
            owner=self.alice, description="Shoes", mode="part_load", origin="mombasa", destination="kampala", quantity=20, packages_received=20,
            weight_kg=Decimal("100"), volume_cbm=Decimal("1.000"), charge_usd=Decimal("950"), payment_status="unpaid",
            trip=self.flight1,
        )
        self.alice_goods.update_status(ShipmentStatus.CONFIRMED)
        self.bob_goods = Shipment.objects.create(owner=self.bob, description="Phones", mode="parcel", trip=self.flight1)

    def split(self, **body):
        login_as(self.client, self.ops)
        return self.client.post(f"/api/staff/shipments/{self.alice_goods.tracking_number}/split/", body, format="json")

    def test_split_moves_cargo_into_a_part_on_another_truck(self):
        res = self.split(packages=8, weight_kg="40", volume_cbm="0.4", charge_usd="380", trip=self.flight2.code)
        self.assertEqual(res.status_code, 201, res.data)
        part = Shipment.objects.get(tracking_number=res.data["part"]["tracking_number"])
        self.alice_goods.refresh_from_db()
        self.assertEqual(part.owner, self.alice)
        self.assertEqual(part.parent, self.alice_goods)
        self.assertEqual(part.trip, self.flight2)
        self.assertEqual((part.origin, part.destination), ("mombasa", "kampala"))
        self.assertEqual((part.packages_received, part.weight_kg, part.charge_usd), (8, Decimal("40"), Decimal("380")))
        self.assertEqual((self.alice_goods.packages_received, self.alice_goods.weight_kg, self.alice_goods.charge_usd), (12, Decimal("60"), Decimal("570")))
        self.assertEqual(part.payment_status, "unpaid")
        self.assertEqual(self.flight1.used_kg() + self.flight2.used_kg(), Decimal("100"))  # nothing double-counted
        self.assertTrue(part.events.filter(status=ShipmentStatus.CONFIRMED).exists())  # history carried over

    def test_parts_move_independently_with_their_trip(self):
        part = Shipment.objects.get(tracking_number=self.split(packages=5, trip=self.flight2.code).data["part"]["tracking_number"])
        self.flight1.apply_shipment_status(ShipmentStatus.IN_TRANSIT)
        self.alice_goods.refresh_from_db()
        part.refresh_from_db()
        self.assertEqual(self.alice_goods.status, ShipmentStatus.IN_TRANSIT)
        self.assertEqual(part.status, ShipmentStatus.CONFIRMED)

    def test_splitting_a_part_keeps_one_level(self):
        part_tn = self.split(packages=10).data["part"]["tracking_number"]
        login_as(self.client, self.ops)
        res = self.client.post(f"/api/staff/shipments/{part_tn}/split/", {"packages": 4}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Shipment.objects.get(tracking_number=res.data["part"]["tracking_number"]).parent, self.alice_goods)
        self.assertEqual(self.alice_goods.parts.count(), 2)

    def test_split_validation(self):
        self.assertEqual(self.split(packages=20).status_code, 400)  # must leave something behind
        self.assertEqual(self.split(packages=2, weight_kg="500").status_code, 400)
        self.assertEqual(self.split(packages=2, mode="parcel", trip=self.flight2.code).status_code, 201)
        self.flight2.status = "in_transit"
        self.flight2.save()
        self.assertEqual(self.split(packages=2, trip=self.flight2.code).status_code, 400)  # truck already left

    def test_only_cargo_not_yet_loaded_can_be_split(self):
        self.alice_goods.update_status(ShipmentStatus.LOADED)
        self.assertEqual(self.split(packages=2).status_code, 400)

    def test_customer_sees_own_parts_only(self):
        part_tn = self.split(packages=8, trip=self.flight2.code).data["part"]["tracking_number"]
        login_as(self.client, self.alice)
        listing = self.client.get("/api/shipments/").data["results"]
        self.assertEqual({s["tracking_number"] for s in listing}, {self.alice_goods.tracking_number, part_tn})
        detail = self.client.get(f"/api/shipments/{part_tn}/").data
        self.assertEqual(detail["part"]["number"], 2)
        self.assertEqual(detail["part"]["count"], 2)
        self.assertEqual(detail["part"]["original"], self.alice_goods.tracking_number)

    def test_customers_sharing_a_truck_see_nothing_of_each_other(self):
        self.split(packages=8, trip=self.flight2.code)
        login_as(self.client, self.bob)
        listing = self.client.get("/api/shipments/").data["results"]
        self.assertEqual([s["tracking_number"] for s in listing], [self.bob_goods.tracking_number])
        self.assertIsNone(listing[0]["part"])
        self.assertEqual(self.client.get(f"/api/shipments/{self.alice_goods.tracking_number}/").status_code, 404)
        self.assertEqual(self.client.get("/api/shipments/summary/").data["total"], 1)
        self.assertEqual(self.client.get(f"/api/shipments/?trip={self.flight1.code}").data["count"], 1)
        # the public tracker shows status only: no owner, trip, contents or other customers
        public = self.client.get(f"/api/track/{self.alice_goods.tracking_number}/").data
        self.assertFalse({"owner", "trip_code", "trip", "description", "part", "charge_usd"} & set(public))

    def test_split_needs_add_and_change_permission(self):
        support = User.objects.create_user("help@example.com", PW, first_name="H", last_name="S", is_staff=True)
        support.groups.add(Group.objects.get(name="Customer support"))  # shipments: view only
        login_as(self.client, User.objects.get(pk=support.pk))
        res = self.client.post(f"/api/staff/shipments/{self.alice_goods.tracking_number}/split/", {"packages": 2}, format="json")
        self.assertEqual(res.status_code, 403)
