from rest_framework.permissions import BasePermission

from .scopes import ACCOUNT, DRIVER, has_scope


class IsAccountUser(BasePermission):
    """Signed-in user whose token carries the `account` scope (customer self-service).
    This is the API-wide default permission."""

    message = "This token is not allowed to access account data."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and has_scope(request, ACCOUNT))


class IsDriver(BasePermission):
    """Active driver account whose token carries the `driver` scope. Drivers
    only ever reach trips allocated to them (enforced by each view's queryset)."""

    message = "This sign-in is not allowed to use the driver app."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_active and getattr(user, "is_driver", False)
            and has_scope(request, DRIVER)
        )
