import logging

from rest_framework.views import exception_handler

logger = logging.getLogger("security")


def api_exception_handler(exc, context):
    """DRF handler that logs auth/permission failures, and returns a generic
    500 so stack traces and internals never reach the client."""
    response = exception_handler(exc, context)
    request = context.get("request")
    if response is not None and response.status_code in (401, 403, 429) and request is not None:
        logger.info(
            "api_denied status=%s path=%s ip=%s",
            response.status_code,
            request.path,
            request.META.get("REMOTE_ADDR"),
        )
    if response is None:
        logger.exception("unhandled_api_error path=%s", getattr(request, "path", "?"))
        from rest_framework.response import Response

        return Response({"detail": "An unexpected error occurred."}, status=500)
    return response
