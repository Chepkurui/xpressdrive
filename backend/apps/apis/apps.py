from django.apps import AppConfig


class ApisConfig(AppConfig):
    """Hosts every /api/ route. Views live in their feature apps."""

    name = "apps.apis"
    label = "apis"
    verbose_name = "API routes"
