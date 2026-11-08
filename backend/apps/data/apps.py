from django.apps import AppConfig


class DataConfig(AppConfig):
    """Single home for every database model in the platform."""

    name = "apps.data"
    label = "data"
    verbose_name = "XpressDrive data"
