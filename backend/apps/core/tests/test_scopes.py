from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.core.testing import login_as
from apps.data.models import ShippingRate

User = get_user_model()
PW = "x-Strong-Pass-123"


def grant(user, *codenames):
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label="data", codename__in=codenames))
    return User.objects.get(pk=user.pk)


class TokenScopeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user("cust@example.com", PW, first_name="C", last_name="C")
        self.pricer = User.objects.create_user("price@example.com", PW, first_name="P", last_name="M", is_staff=True)
        self.pricer.groups.add(Group.objects.get(name="Pricing manager"))
        self.pricer = User.objects.get(pk=self.pricer.pk)

    def login(self, email, mobile=False, **extra):
        headers = {"HTTP_X_CLIENT": "mobile"} if mobile else {}
        return self.client.post("/api/auth/login/", {"email": email, "password": PW, **extra}, format="json", **headers)

    def test_login_token_carries_role_scopes(self):
        res = self.login("price@example.com")
        self.assertEqual(res.status_code, 200, res.data)
        scopes = set(AccessToken(res.data["access"])["scope"].split())
        self.assertEqual(res.data["scope"], AccessToken(res.data["access"])["scope"])
        self.assertTrue({"account", "staff", "staff:rates:add", "staff:rates:delete"} <= scopes)
        self.assertNotIn("staff:shipments:view", scopes)

    def test_customer_token_has_account_scope_only(self):
        res = self.login("cust@example.com")
        self.assertEqual(AccessToken(res.data["access"])["scope"], "account")

    def test_mobile_token_never_gets_staff_scopes(self):
        res = self.login("price@example.com", mobile=True)
        token = res.data["access"]
        self.assertEqual(AccessToken(token)["scope"], "account")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 403)
        self.assertEqual(self.client.get("/api/staff/summary/").status_code, 403)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_narrowed_token_cannot_exceed_requested_scope(self):
        res = self.login("price@example.com", scope="staff staff:rates:view")
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 200)
        res = self.client.post("/api/staff/rates/", {"name": "X", "mode": "part_load", "price_usd": "1", "transit_days_min": 1, "transit_days_max": 2, "summary": "x"}, format="json")
        self.assertEqual(res.status_code, 403)
        # no "account" scope requested -> customer endpoints are closed to this token too
        self.assertEqual(self.client.get("/api/shipments/").status_code, 403)

    def test_unknown_scope_is_rejected(self):
        self.assertEqual(self.login("price@example.com", scope="staff:everything").status_code, 400)

    def test_token_cannot_be_widened_by_role_change_until_refresh(self):
        clerk = User.objects.create_user("clerk@example.com", PW, first_name="K", last_name="K", is_staff=True)
        refresh = login_as(self.client, clerk)
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 403)
        clerk = grant(clerk, "view_shippingrate")
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 403)  # old token, old scope
        res = self.client.post("/api/auth/refresh/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn("staff:rates:view", res.data["scope"].split())
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 200)

    def test_role_removal_applies_to_existing_tokens_immediately(self):
        login_as(self.client, self.pricer)
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 200)
        self.pricer.groups.clear()
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 403)

    def test_refresh_keeps_a_narrowed_token_narrow(self):
        refresh = login_as(self.client, self.pricer, scope={"staff", "staff:rates:view"})
        res = self.client.post("/api/auth/refresh/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(set(res.data["scope"].split()), {"staff", "staff:rates:view"})

    def test_mobile_refresh_never_gains_staff_scopes(self):
        legacy = RefreshToken.for_user(self.pricer)  # pre-scope refresh token: no client claim
        res = self.client.post("/api/auth/refresh/", {"refresh": str(legacy)}, format="json", HTTP_X_CLIENT="mobile")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["scope"], "account")

    def test_token_without_scope_is_rejected_with_401(self):
        legacy = RefreshToken.for_user(self.customer).access_token  # minted the old way: no scope claim
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {legacy}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_me_reports_token_scope(self):
        login_as(self.client, self.pricer, scope={"account", "staff", "staff:rates:view"})
        me = self.client.get("/api/auth/me/").data
        self.assertEqual(me["staff_access"]["rates"], {"view": True, "add": False, "change": False, "delete": False})
        self.assertEqual(me["token_scope"], ["account", "staff", "staff:rates:view"])


class PricingPlanTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.pricer = User.objects.create_user("price@example.com", PW, first_name="P", last_name="M", is_staff=True)
        self.pricer.groups.add(Group.objects.get(name="Pricing manager"))
        self.pricer = User.objects.get(pk=self.pricer.pk)
        self.support = User.objects.create_user("help@example.com", PW, first_name="H", last_name="S", is_staff=True)
        self.support.groups.add(Group.objects.get(name="Customer support"))
        self.support = User.objects.get(pk=self.support.pk)
        self.plan = {"name": "Parcel — Express Kampala Nairobi", "mode": "parcel", "price_usd": "15.50", "min_charge_usd": "40",
                     "origin": "kampala", "destination": "nairobi",
                     "transit_days_min": 1, "transit_days_max": 2, "summary": "Next-day parcels between the capitals."}

    def test_existing_rates_became_plans(self):
        codes = set(ShippingRate.objects.values_list("code", flat=True))
        self.assertTrue({"parcel", "part-load", "full-truck", "container-20", "container-40", "backhaul-40"} <= codes)
        self.assertFalse({"air_express", "sea"} & codes)

    def test_pricing_manager_can_add_edit_and_delete_plans(self):
        login_as(self.client, self.pricer)
        res = self.client.post("/api/staff/rates/", self.plan, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["code"], "parcel-express-kampala-nairobi")
        self.assertEqual(res.data["route_display"], "Kampala → Nairobi")
        self.assertEqual(res.data["basis"], "per_kg")  # follows the mode
        url = f"/api/staff/rates/{res.data['code']}/"
        self.assertEqual(self.client.patch(url, {"price_usd": "14"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"mode": "part_load"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_codes_are_unique(self):
        login_as(self.client, self.pricer)
        first = self.client.post("/api/staff/rates/", self.plan, format="json").data["code"]
        second = self.client.post("/api/staff/rates/", self.plan, format="json").data["code"]
        self.assertNotEqual(first, second)
        res = self.client.post("/api/staff/rates/", {**self.plan, "code": first}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_view_only_role_cannot_add_or_delete(self):
        login_as(self.client, self.support)
        self.assertEqual(self.client.get("/api/staff/rates/").status_code, 200)
        self.assertEqual(self.client.post("/api/staff/rates/", self.plan, format="json").status_code, 403)
        self.assertEqual(self.client.delete("/api/staff/rates/part-load/").status_code, 403)

    def test_new_plan_is_public_and_estimable(self):
        login_as(self.client, self.pricer)
        code = self.client.post("/api/staff/rates/", self.plan, format="json").data["code"]
        self.client.credentials()
        self.assertIn(code, [r["code"] for r in self.client.get("/api/rates/").data])
        res = self.client.post("/api/rates/estimate/", {"plan": code, "weight_kg": "2"}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["plan"], code)
        self.assertEqual(res.data["cost_low_usd"], "40.00")  # 2kg x 15.50 = 31 -> minimum 40
        # mode-only requests still work (older mobile builds) and use the mode's first plan
        res = self.client.post("/api/rates/estimate/", {"mode": "parcel", "weight_kg": "2"}, format="json")
        self.assertEqual(res.data["plan"], "parcel")

    def test_inactive_plan_is_hidden_and_not_estimable(self):
        ShippingRate.objects.filter(code="part-load").update(is_active=False)
        self.assertNotIn("part-load", [r["code"] for r in self.client.get("/api/rates/").data])
        res = self.client.post("/api/rates/estimate/", {"plan": "part-load", "weight_kg": "2"}, format="json")
        self.assertEqual(res.status_code, 400)
