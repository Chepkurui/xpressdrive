from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase

from apps.core.testing import login_as

User = get_user_model()
PASSWORD = "Kampala-Cargo-2026!"
XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class AuthFlowTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("jane@example.com", PASSWORD, first_name="Jane", last_name="N")

    def test_register_assigns_customer_code_and_hashes_password(self):
        res = self.client.post("/api/auth/register/", {
            "email": "New@Example.com", "password": PASSWORD, "first_name": "A", "last_name": "B", "phone": "+256700000000",
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["customer_code"].startswith("XD"))
        self.assertNotIn("password", res.data)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.password.startswith("argon2"))

    def test_register_rejects_weak_password(self):
        res = self.client.post("/api/auth/register/", {
            "email": "weak@example.com", "password": "12345678", "first_name": "A", "last_name": "B", "phone": "+256700000000",
        }, format="json")
        self.assertEqual(res.status_code, 400)

    def test_register_ignores_privilege_fields(self):
        self.client.post("/api/auth/register/", {
            "email": "sneaky@example.com", "password": PASSWORD, "first_name": "A", "last_name": "B",
            "phone": "+256700000000", "is_staff": True, "is_superuser": True,
        }, format="json")
        user = User.objects.get(email="sneaky@example.com")
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_web_login_sets_httponly_cookie_and_hides_refresh(self):
        res = self.client.post("/api/auth/login/", {"email": "JANE@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
        self.assertNotIn("refresh", res.data)
        cookie = res.cookies["xd_refresh"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")

    def test_mobile_login_returns_refresh_in_body(self):
        res = self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": PASSWORD}, format="json", HTTP_X_CLIENT="mobile")
        self.assertIn("refresh", res.data)
        self.assertNotIn("xd_refresh", res.cookies)

    def test_bad_credentials_generic_error(self):
        res = self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": "wrong"}, format="json")
        self.assertEqual(res.status_code, 401)
        res2 = self.client.post("/api/auth/login/", {"email": "nobody@example.com", "password": "wrong"}, format="json")
        self.assertEqual(res.data, res2.data)

    def test_login_is_throttled(self):
        for _ in range(5):
            self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": "wrong"}, format="json")
        res = self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": "wrong"}, format="json")
        self.assertEqual(res.status_code, 429)

    def test_cookie_refresh_requires_custom_header(self):
        self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(self.client.post("/api/auth/refresh/").status_code, 403)
        res = self.client.post("/api/auth/refresh/", **XHR)
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_refresh_rotation_blacklists_old_token(self):
        login = self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": PASSWORD}, format="json", HTTP_X_CLIENT="mobile")
        old = login.data["refresh"]
        ok = self.client.post("/api/auth/refresh/", {"refresh": old}, format="json", HTTP_X_CLIENT="mobile")
        self.assertEqual(ok.status_code, 200)
        reused = self.client.post("/api/auth/refresh/", {"refresh": old}, format="json", HTTP_X_CLIENT="mobile")
        self.assertEqual(reused.status_code, 401)

    def test_logout_revokes_refresh(self):
        login = self.client.post("/api/auth/login/", {"email": "jane@example.com", "password": PASSWORD}, format="json", HTTP_X_CLIENT="mobile")
        refresh = login.data["refresh"]
        self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
        res = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_me_requires_auth_and_email_is_read_only(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        login_as(self.client, self.user)
        res = self.client.patch("/api/auth/me/", {"email": "evil@example.com", "first_name": "Janet"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "jane@example.com")
        self.assertEqual(self.user.first_name, "Janet")
        self.assertFalse(res.data["is_driver"])

    def test_password_reset_does_not_enumerate(self):
        a = self.client.post("/api/auth/password/reset/", {"email": "jane@example.com"}, format="json")
        b = self.client.post("/api/auth/password/reset/", {"email": "ghost@example.com"}, format="json")
        self.assertEqual(a.status_code, b.status_code)
        self.assertEqual(a.data, b.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_confirm(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        res = self.client.post("/api/auth/password/reset/confirm/", {"uid": uid, "token": token, "new_password": "Another-Strong-Pass-99"}, format="json")
        self.assertEqual(res.status_code, 200)
        reuse = self.client.post("/api/auth/password/reset/confirm/", {"uid": uid, "token": token, "new_password": "Yet-Another-Pass-77"}, format="json")
        self.assertEqual(reuse.status_code, 400)
