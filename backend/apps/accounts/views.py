import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import IsAccountUser

from .serializers import (
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    ScopedTokenRefreshSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tokens import revoke_all_refresh_tokens

User = get_user_model()
logger = logging.getLogger("security")


def client_ip(request):
    return request.META.get("REMOTE_ADDR", "")


class RefreshCookieMixin:
    """Web clients keep the refresh token in an httpOnly cookie (out of reach
    of XSS). Mobile clients send `X-Client: mobile` and receive it in the body
    to store in the OS secure keystore."""

    def get_authenticate_header(self, request):
        # These views skip access-token auth, but token failures must still be
        # 401 (not 403) so clients know to re-authenticate.
        return 'Bearer realm="api"'

    def is_mobile(self, request):
        return request.headers.get("X-Client", "").lower() == "mobile"

    def set_refresh_cookie(self, response, refresh):
        cfg = settings.AUTH_REFRESH_COOKIE
        response.set_cookie(
            cfg["name"],
            refresh,
            max_age=cfg["max_age"],
            path=cfg["path"],
            secure=cfg["secure"],
            httponly=True,
            samesite=cfg["samesite"],
        )

    def clear_refresh_cookie(self, response):
        cfg = settings.AUTH_REFRESH_COOKIE
        response.delete_cookie(cfg["name"], path=cfg["path"], samesite=cfg["samesite"])

    def deliver_tokens(self, request, response):
        refresh = response.data.get("refresh")
        if refresh and not self.is_mobile(request):
            self.set_refresh_cookie(response, refresh)
            del response.data["refresh"]
        return response

    def read_refresh(self, request):
        """Return (token, came_from_cookie)."""
        token = request.data.get("refresh") if hasattr(request.data, "get") else None
        if token:
            return token, False
        return request.COOKIES.get(settings.AUTH_REFRESH_COOKIE["name"]), True

    def require_csrf_header_for_cookie(self, request, from_cookie):
        # Custom header forces a CORS preflight, so cross-site forms cannot
        # ride the cookie (defence in depth on top of SameSite=Strict).
        if from_cookie and request.headers.get("X-Requested-With") != "XMLHttpRequest":
            raise PermissionDenied("Missing required header.")


class RegisterView(CreateAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RegisterSerializer
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("user_registered user_id=%s ip=%s", user.pk, client_ip(request))
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(RefreshCookieMixin, TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            logger.warning("login_failed ip=%s", client_ip(request))
            raise
        logger.info("login_success ip=%s", client_ip(request))
        return self.deliver_tokens(request, response)


class RefreshView(RefreshCookieMixin, GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "token_refresh"

    def post(self, request):
        token, from_cookie = self.read_refresh(request)
        self.require_csrf_header_for_cookie(request, from_cookie)
        if not token:
            raise InvalidToken("No refresh token provided.")
        serializer = ScopedTokenRefreshSerializer(data={"refresh": token}, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        return self.deliver_tokens(request, response)


class LogoutView(RefreshCookieMixin, GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token, from_cookie = self.read_refresh(request)
        self.require_csrf_header_for_cookie(request, from_cookie)
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        self.clear_refresh_cookie(response)
        return response


class MeView(RetrieveUpdateAPIView):
    permission_classes = [IsAccountUser]
    serializer_class = UserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class ChangePasswordView(RefreshCookieMixin, GenericAPIView):
    permission_classes = [IsAccountUser]
    serializer_class = ChangePasswordSerializer
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        revoke_all_refresh_tokens(user)
        logger.info("password_changed user_id=%s ip=%s", user.pk, client_ip(request))
        response = Response({"detail": "Password updated. Please sign in again."})
        self.clear_refresh_cookie(response)
        return response


def send_password_reset_email(user):
    """Email a one-hour password reset link. Also used by the staff portal."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        "Reset your XpressDrive password",
        f"Hello {user.first_name or ''},\n\nUse the link below to set a new password. "
        f"It expires in 1 hour.\n\n{link}\n\nIf you did not request this, ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


class PasswordResetRequestView(GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetRequestSerializer
    throttle_scope = "password_reset"
    GENERIC = "If an account exists for that email, a reset link has been sent."

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            send_password_reset_email(user)
            logger.info("password_reset_requested user_id=%s ip=%s", user.pk, client_ip(request))
        # Identical response whether or not the account exists (no enumeration).
        return Response({"detail": self.GENERIC})


class PasswordResetConfirmView(GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetConfirmSerializer
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invalid = ValidationError({"detail": "This reset link is invalid or has expired."})
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise invalid
        if not default_token_generator.check_token(user, data["token"]):
            raise invalid
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            validate_password(data["new_password"], user=user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": list(exc.messages)})
        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        revoke_all_refresh_tokens(user)
        logger.info("password_reset_completed user_id=%s ip=%s", user.pk, client_ip(request))
        return Response({"detail": "Your password has been reset. You can now sign in."})
