from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.scopes import ACTIONS, CLIENT_MOBILE, CLIENT_WEB, STAFF_SECTIONS, issue_tokens, parse_scope, staff_can, token_scopes

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    staff_access = serializers.SerializerMethodField()
    token_scope = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "customer_code",
            "date_joined",
            "is_staff",
            "is_driver",
            "staff_access",
            "token_scope",
        ]
        read_only_fields = ["email", "customer_code", "date_joined", "is_staff", "is_driver"]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False, "max_length": 80},
            "last_name": {"required": True, "allow_blank": False, "max_length": 80},
        }

    def get_staff_access(self, obj):
        """Which staff-portal sections this sign-in may view/add/change/delete
        (None for customers). Reflects BOTH the user's role (Django permissions,
        same as the admin) and the scope of the token used for this request."""
        if not (obj.is_staff and obj.is_active):
            return None
        request = self.context.get("request")
        if request is None or request.user != obj:
            return None
        return {
            section: {action: staff_can(request, model, action) for action in ACTIONS}
            for section, model in STAFF_SECTIONS.items()
        }

    def get_token_scope(self, obj):
        request = self.context.get("request")
        if request is None or request.user != obj:
            return []
        return sorted(token_scopes(request))


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone"]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False, "max_length": 80},
            "last_name": {"required": True, "allow_blank": False, "max_length": 80},
            "phone": {"required": True, "allow_blank": False},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        validate_password(attrs["password"], user=candidate)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


def _client(request):
    return CLIENT_MOBILE if request is not None and request.headers.get("X-Client", "").lower() == CLIENT_MOBILE else CLIENT_WEB


def _token_payload(refresh):
    return {"refresh": str(refresh), "access": str(refresh.access_token), "scope": refresh["scope"]}


class EmailTokenObtainPairSerializer(TokenObtainSerializer):
    """Sign in with email + password. The tokens are limited to what the user's
    role allows (and to `scope`, if the client asks for less)."""

    token_class = RefreshToken
    scope = serializers.CharField(required=False, allow_blank=True, max_length=1000,
                                  help_text="Optional space-separated subset of scopes to request.")

    def validate_scope(self, value):
        try:
            return parse_scope(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        attrs[self.username_field] = attrs.get(self.username_field, "").strip().lower()
        requested = attrs.pop("scope", None)
        super().validate(attrs)  # authenticates and sets self.user
        refresh = issue_tokens(self.user, _client(self.context.get("request")), requested, update_login=True)
        return _token_payload(refresh)


class ScopedTokenRefreshSerializer(serializers.Serializer):
    """Rotate a refresh token. Scopes are recomputed from the user's CURRENT role,
    so promotions/demotions reach the token on refresh."""

    refresh = serializers.CharField()

    def validate(self, attrs):
        old = RefreshToken(attrs["refresh"])  # verifies signature, expiry and blacklist
        user = User.objects.filter(pk=old.get(jwt_settings.USER_ID_CLAIM), is_active=True).first()
        if user is None:
            raise AuthenticationFailed("User is inactive or no longer exists.", code="user_inactive")
        if jwt_settings.ROTATE_REFRESH_TOKENS and jwt_settings.BLACKLIST_AFTER_ROTATION:
            old.blacklist()
        requested = set(str(old.get("scope_req", "")).split()) or None
        # Mobile if the token says so OR this request comes from the app (covers
        # tokens issued before the `client` claim existed). Never upgrades to web.
        client = old.get("client", CLIENT_WEB)
        if _client(self.context.get("request")) == CLIENT_MOBILE:
            client = CLIENT_MOBILE
        refresh = issue_tokens(user, client, requested)
        if not jwt_settings.ROTATE_REFRESH_TOKENS:
            return {"access": str(refresh.access_token), "scope": refresh["scope"]}
        return _token_payload(refresh)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False, max_length=128)
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        validate_password(attrs["new_password"], user=self.context["request"].user)
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)
