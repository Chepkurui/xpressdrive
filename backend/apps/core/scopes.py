"""Scoped API tokens.

Every access/refresh token carries a `scope` claim (space-separated, OAuth style)
derived from the user's role at the time it was issued:

    account                     customer self-service (own profile & bookings)
    driver                      driver app: own allocated trips, positions, empty legs
    staff                       staff portal entry (dashboard); sections need more
    staff:<section>:<action>    e.g. staff:rates:add, staff:shipments:change

A request is allowed only if BOTH hold:
  1. the token's scope includes the operation, and
  2. the user's *current* role (Django groups/permissions) still allows it.

So a role downgrade bites on the very next request, a role upgrade takes effect
at the next token refresh, and a token can never do more than it was issued for.
Tokens issued to the mobile app (X-Client: mobile) carry `account` (and
`driver` for drivers) but never staff scopes, and a
client may ask for a narrower scope at sign-in (e.g. an integration script that
only needs `staff:shipments:view`).
"""
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

ACCOUNT = "account"
DRIVER = "driver"
STAFF = "staff"
ACTIONS = ("view", "add", "change", "delete")

# Staff-portal section -> model whose Django permissions guard it.
# Same permissions as the Django admin, so one set of grants controls both.
STAFF_SECTIONS = {
    "shipments": "shipment",
    "trips": "trip",
    "trucks": "truck",
    "emptylegs": "emptyleg",
    "users": "user",
    "rates": "shippingrate",
    "messages": "contactmessage",
}
MODEL_SECTIONS = {model: section for section, model in STAFF_SECTIONS.items()}

CLIENT_WEB = "web"
CLIENT_MOBILE = "mobile"
CLIENTS = {CLIENT_WEB, CLIENT_MOBILE}


def staff_scope(section, action):
    return f"staff:{section}:{action}"


ALL_SCOPES = frozenset({ACCOUNT, DRIVER, STAFF} | {staff_scope(s, a) for s in STAFF_SECTIONS for a in ACTIONS})


def role_scopes(user, client=CLIENT_WEB):
    """Everything this user's current role allows, for this kind of client."""
    if not (user and user.is_active):
        return set()
    scopes = {ACCOUNT}
    if getattr(user, "is_driver", False):
        scopes.add(DRIVER)
    if client == CLIENT_MOBILE or not user.is_staff:
        return scopes  # the mobile app has no staff features: never hand it staff powers
    scopes.add(STAFF)
    for section, model in STAFF_SECTIONS.items():
        for action in ACTIONS:
            if user.has_perm(f"data.{action}_{model}"):
                scopes.add(staff_scope(section, action))
    return scopes


def parse_scope(value):
    """'a b c' -> {'a','b','c'}; unknown names are rejected."""
    if not value:
        return None
    requested = set(str(value).split())
    unknown = requested - ALL_SCOPES
    if unknown:
        raise ValueError(f"Unknown scope: {' '.join(sorted(unknown))}")
    return requested


def issue_tokens(user, client=CLIENT_WEB, requested=None, update_login=False):
    """Mint a refresh/access pair limited to the user's role (and the requested subset)."""
    client = client if client in CLIENTS else CLIENT_WEB
    granted = role_scopes(user, client)
    if requested is not None:
        granted &= set(requested)
    refresh = RefreshToken.for_user(user)
    refresh["scope"] = " ".join(sorted(granted))
    refresh["client"] = client
    if requested is not None:
        refresh["scope_req"] = " ".join(sorted(requested))  # kept so refreshes stay narrowed
    if update_login and api_settings.UPDATE_LAST_LOGIN:
        update_last_login(None, user)
    return refresh


def token_scopes(request):
    token = getattr(request, "auth", None)
    if token is None or not hasattr(token, "get"):
        return frozenset()
    return frozenset(str(token.get("scope", "")).split())


def has_scope(request, scope):
    return scope in token_scopes(request)


def staff_can(request, model, action="view"):
    """Token scope AND live role permission. Used by staff views and /auth/me."""
    user = request.user
    if not (user and user.is_authenticated and user.is_active and user.is_staff):
        return False
    section = MODEL_SECTIONS.get(model)
    if section is None or not has_scope(request, staff_scope(section, action)):
        return False
    return user.has_perm(f"data.{action}_{model}")
