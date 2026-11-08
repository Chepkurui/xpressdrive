from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class ScopedJWTAuthentication(JWTAuthentication):
    """JWT auth that refuses tokens without a `scope` claim.

    Tokens minted before scopes existed get a 401, which makes clients refresh
    (or sign in again) and receive a properly scoped token.
    """

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if "scope" not in token:
            raise InvalidToken("Token has no scope. Please sign in again.")
        return token
