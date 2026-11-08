class SecurityHeadersMiddleware:
    """Adds headers Django does not set by default.

    API responses are JSON only, so they get a lock-down CSP. The admin keeps
    a same-origin CSP so its own static assets still load.
    """

    API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ADMIN_CSP = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response.setdefault("Content-Security-Policy", self.API_CSP)
            response.setdefault("Cache-Control", "no-store")
        else:
            response.setdefault("Content-Security-Policy", self.ADMIN_CSP)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return response
