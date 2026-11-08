from rest_framework.permissions import BasePermission

from apps.core.scopes import MODEL_SECTIONS, STAFF, STAFF_SECTIONS, has_scope, staff_can  # noqa: F401 (re-exported)

_ACTION_FOR_METHOD = {"GET": "view", "HEAD": "view", "OPTIONS": "view", "POST": "change", "PUT": "change", "PATCH": "change", "DELETE": "delete"}


class IsStaffWithModelPerm(BasePermission):
    """Active staff account AND the Django model permission AND a token scope
    for this request.

    Views set `staff_model` (e.g. "shipment"). Reads need data.view_<model>;
    writes need data.change_<model>, deletes data.delete_<model>, and POST needs
    data.add_<model> when the view sets `staff_post_action = "add"`. The token
    must carry the matching `staff:<section>:<action>` scope as well, so a
    token can never exceed either the role it was issued for or the role the
    user holds now. Superusers still need a scoped token.
    """

    message = "Your role or sign-in token does not allow this operation."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active and user.is_staff):
            return False
        model = getattr(view, "staff_model", None)
        if model is None:
            # e.g. the staff dashboard, which filters by permission itself; still
            # needs a token issued for staff use (never a mobile/customer token).
            return has_scope(request, STAFF)
        action = _ACTION_FOR_METHOD.get(request.method, "change")
        if request.method == "POST":
            action = getattr(view, "staff_post_action", "change")
        return staff_can(request, model, action)
