from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .places import PLACE_CHOICES, place_name


class ShippingMode(models.TextChoices):
    """How much of a truck the customer's cargo takes, from one parcel up to a full container."""

    PARCEL = "parcel", "Parcel / small goods"
    PART_LOAD = "part_load", "Part load (shared truck)"
    FULL_TRUCK = "full_truck", "Full truck load"
    CONTAINER_20 = "container_20", "20ft container"
    CONTAINER_40 = "container_40", "40ft container"


class RateBasis(models.TextChoices):
    PER_KG = "per_kg", "Per kilogram (chargeable weight)"
    PER_CBM = "per_cbm", "Per cubic metre (CBM)"
    PER_CONTAINER = "per_container", "Per truck / container"


# Each load type is charged on one basis.
BASIS_FOR_MODE = {
    ShippingMode.PARCEL: RateBasis.PER_KG,
    ShippingMode.PART_LOAD: RateBasis.PER_CBM,
    ShippingMode.FULL_TRUCK: RateBasis.PER_CONTAINER,
    ShippingMode.CONTAINER_20: RateBasis.PER_CONTAINER,
    ShippingMode.CONTAINER_40: RateBasis.PER_CONTAINER,
}


class ShippingRate(models.Model):
    """A pricing plan on the public rate card. Staff can add as many plans per
    load type as they like, optionally for one lane (e.g. "Mombasa → Kampala,
    40ft"); the estimator uses the plan the customer picks, or the first
    active plan for a load type."""

    code = models.SlugField(max_length=40, unique=True, help_text="Short, permanent identifier used in URLs and the API.")
    name = models.CharField(max_length=80)
    mode = models.CharField("Load type", max_length=20, choices=ShippingMode.choices)
    basis = models.CharField(max_length=20, choices=RateBasis.choices)
    origin = models.CharField(max_length=30, choices=PLACE_CHOICES, blank=True, help_text="Leave blank for any route.")
    destination = models.CharField(max_length=30, choices=PLACE_CHOICES, blank=True, help_text="Leave blank for any route.")
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    min_charge_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    transit_days_min = models.PositiveSmallIntegerField()
    transit_days_max = models.PositiveSmallIntegerField()
    summary = models.CharField(max_length=200)
    best_for = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "pricing plan"

    def save(self, *args, **kwargs):
        self.basis = BASIS_FOR_MODE.get(self.mode, self.basis)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} — ${self.price_usd} {self.get_basis_display()}"

    @property
    def route_display(self):
        if not (self.origin or self.destination):
            return ""
        return f"{place_name(self.origin) or 'Any'} → {place_name(self.destination) or 'Any'}"

    @classmethod
    def default_for_mode(cls, mode):
        return cls.objects.filter(mode=mode, is_active=True).order_by("sort_order", "pk").first()
