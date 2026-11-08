"""
Django settings for the XpressDrive platform (regional road freight & backhaul matching).

All secrets and environment-specific values come from environment variables
(optionally loaded from backend/.env). Defaults are production-safe: DEBUG is
off and a missing SECRET_KEY is a hard error outside of DEBUG.
"""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-secret-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG is off.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.data",  # all models
    "apps.apis",  # all /api/ routes
    "apps.core",
    "apps.accounts",
    "apps.pricing",
    "apps.shipments",
    "apps.staff",
    "apps.fleet",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database (PostgreSQL). USE_SQLITE=1 exists only for quick local test runs.
# --------------------------------------------------------------------------
if env_bool("USE_SQLITE", False):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "xpressdrive"),
            "USER": env("POSTGRES_USER", "xpressdrive"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(env("POSTGRES_CONN_MAX_AGE", "60")),
            "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", "prefer")},
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "data.User"

# --------------------------------------------------------------------------
# Passwords (OWASP: strong adaptive hashing + length/complexity checks)
# --------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour

# --------------------------------------------------------------------------
# I18N
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kampala"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --------------------------------------------------------------------------
# Request size limits (DoS hardening)
# --------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 1 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200

# --------------------------------------------------------------------------
# Caching (used by throttling). Use Redis in production so throttles are
# shared between workers.
# --------------------------------------------------------------------------
if env("REDIS_URL"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env("REDIS_URL")}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # API is token-only: no session auth, so no ambient-credential CSRF risk.
        "apps.core.authentication.ScopedJWTAuthentication",  # every token carries a role-derived scope
    ],
    "DEFAULT_PERMISSION_CLASSES": ["apps.core.permissions.IsAccountUser"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", "120/min"),
        "user": env("THROTTLE_USER", "600/min"),
        "login": env("THROTTLE_LOGIN", "5/min"),
        "register": env("THROTTLE_REGISTER", "10/hour"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", "5/hour"),
        "token_refresh": env("THROTTLE_TOKEN_REFRESH", "30/min"),
        "track": env("THROTTLE_TRACK", "30/min"),
        "estimate": env("THROTTLE_ESTIMATE", "60/min"),
        "contact": env("THROTTLE_CONTACT", "5/hour"),
        # Driver phones post batched GPS fixes (every ~20-30 s, more after reconnecting).
        "positions": env("THROTTLE_POSITIONS", "60/min"),
        "capacity": env("THROTTLE_CAPACITY", "60/min"),
    },
    # Only trust X-Forwarded-For for the number of proxies we actually run.
    # 0 = use REMOTE_ADDR (never trust client-supplied headers).
    "NUM_PROXIES": int(env("DJANGO_NUM_PROXIES", "0")),
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "10"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_CLAIM": "user_id",
}

# Refresh-token cookie used by the web client (httpOnly: unreadable by JS).
AUTH_REFRESH_COOKIE = {
    "name": "xd_refresh",
    "path": "/api/auth/",
    "secure": env_bool("AUTH_COOKIE_SECURE", not DEBUG),
    "samesite": "Strict",
    "max_age": int(SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
}

# --------------------------------------------------------------------------
# CORS. Prefer serving web + API from the same site (reverse proxy) so this
# list can stay empty. Never use CORS_ALLOW_ALL_ORIGINS.
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOW_HEADERS = ["accept", "authorization", "content-type", "x-requested-with", "x-client"]
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

# --------------------------------------------------------------------------
# Transport / browser security headers
# --------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8  # admin sessions: 8 hours

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", str(60 * 60 * 24 * 365)))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    if env_bool("DJANGO_BEHIND_PROXY", False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Admin lives at a non-default path in production.
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/")

# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "XpressDrive <no-reply@xpressdrive.co.ug>")

FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5175").rstrip("/")

# --------------------------------------------------------------------------
# Business configuration
# --------------------------------------------------------------------------
ESTIMATE_VARIANCE = float(env("ESTIMATE_VARIANCE", "0.15"))  # +15% upper band on estimates

# --------------------------------------------------------------------------
# Logging (security events go to the "security" logger)
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
