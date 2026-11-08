from decimal import Decimal

from django.core.cache import cache
from rest_framework.test import APITestCase


class EstimateTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_rates_public(self):
        res = self.client.get("/api/rates/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 6)

    def test_parcel_uses_volumetric_weight_when_larger(self):
        # 100x100x60 cm x 2 = 1.2 CBM = 400 kg volumetric (road: /3000) > 100 kg actual; 400 * 0.90 = 360
        res = self.client.post("/api/rates/estimate/", {
            "mode": "parcel", "weight_kg": "50", "quantity": 2, "length_cm": "100", "width_cm": "100", "height_cm": "60",
        }, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(Decimal(res.data["chargeable_quantity"]), Decimal("400"))
        self.assertEqual(Decimal(res.data["cost_low_usd"]), Decimal("360.00"))

    def test_part_load_applies_minimum_charge(self):
        res = self.client.post("/api/rates/estimate/", {
            "mode": "part_load", "weight_kg": "10", "length_cm": "50", "width_cm": "50", "height_cm": "50",
        }, format="json")
        self.assertEqual(Decimal(res.data["cost_low_usd"]), Decimal("60.00"))

    def test_part_load_requires_dimensions(self):
        res = self.client.post("/api/rates/estimate/", {"mode": "part_load", "weight_kg": "10"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_full_container_is_per_container(self):
        res = self.client.post("/api/rates/estimate/", {"plan": "container-40", "weight_kg": "20000", "containers": 2}, format="json")
        self.assertEqual(Decimal(res.data["cost_low_usd"]), Decimal("5200.00"))

    def test_rejects_out_of_range(self):
        res = self.client.post("/api/rates/estimate/", {"mode": "parcel", "weight_kg": "-1"}, format="json")
        self.assertEqual(res.status_code, 400)
