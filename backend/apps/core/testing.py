"""Test helpers: authenticate with a real scoped JWT (not force_authenticate,
which would skip the token-scope checks we want to exercise)."""
from .scopes import CLIENT_WEB, issue_tokens


def login_as(client, user, client_type=CLIENT_WEB, scope=None):
    if user is None:
        client.credentials()
        return None
    refresh = issue_tokens(user, client_type, scope)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return refresh
