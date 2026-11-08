"""Trucks, drivers' empty legs, trip logs and GPS positions.

Positions and trip events with coordinates are for staff (the live trip
dashboard) and the trip's own driver only. Cargo owners see milestones by
place name through TrackingEvent.
"""
from django.conf import settings
from django.db import models

from .places import place_field, place_name


class TruckType(models.TextChoices):
    VAN = "van", "Van / pickup (up to 3 t)"
    RIGID = "rigid", "Rigid truck (5–15 t)"
    FLATBED = "flatbed", "Trailer — flatbed / skeletal"
    BOX_TRAILER = "box_trailer", "Trailer — box / curtain-side"
    CONTAINER_20 = "container_20", "Container carrier — 20ft"
    CONTAINER_40 = "container_40", "Container carrier — 40ft"


class Truck(models.Model):
    plate_number = models.CharField(max_length=20, unique=True)
    trailer_plate = models.CharField(max_length=20, blank=True)
    truck_type = models.CharField(max_length=20, choices=TruckType.choices, default=TruckType.FLATBED)
    make_model = models.CharField(max_length=80, blank=True)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity_cbm = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    home_base = place_field("Home base", blank=True)
    default_driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="trucks", limit_choices_to={"is_driver": True})
    owner_name = models.CharField("Transporter / owner", max_length=120, blank=True)
    owner_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["plate_number"]

    def save(self, *args, **kwargs):
        self.plate_number = " ".join(self.plate_number.upper().split())
        self.trailer_plate = " ".join(self.trailer_plate.upper().split())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plate_number} ({self.get_truck_type_display()})"


class SpaceType(models.TextChoices):
    EMPTY_TRUCK = "empty_truck", "Empty truck"
    EMPTY_CONTAINER_20 = "empty_container_20", "Empty 20ft container"
    EMPTY_CONTAINER_40 = "empty_container_40", "Empty 40ft container"
    PARTIAL = "partial", "Part space available"


class EmptyLegStatus(models.TextChoices):
    OPEN = "open", "Open"
    MATCHED = "matched", "Matched to a trip"
    WITHDRAWN = "withdrawn", "Withdrawn"
    EXPIRED = "expired", "Expired"


class EmptyLeg(models.Model):
    """A driver says: "my truck / container is going back empty on this lane
    on this date". Admins fill it with cargo by turning it into a trip."""

    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="empty_legs")
    truck = models.ForeignKey(Truck, on_delete=models.SET_NULL, null=True, blank=True, related_name="empty_legs")
    vehicle_description = models.CharField(max_length=120, blank=True, help_text="If the truck is not registered yet.")
    origin = place_field("From")
    destination = place_field("To")
    available_from = models.DateField()
    available_until = models.DateField(null=True, blank=True)
    space = models.CharField(max_length=30, choices=SpaceType.choices, default=SpaceType.EMPTY_TRUCK)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity_cbm = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=EmptyLegStatus.choices, default=EmptyLegStatus.OPEN, db_index=True)
    trip = models.OneToOneField("data.Trip", on_delete=models.SET_NULL, null=True, blank=True, related_name="empty_leg")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["available_from", "-created_at"]
        verbose_name = "empty leg"

    def __str__(self):
        return f"{place_name(self.origin)} → {place_name(self.destination)} from {self.available_from}"


class TripEvent(models.Model):
    """Operations log for a trip: allocations, status changes, checkpoints.
    May carry the driver's coordinates, so it is staff/driver only."""

    KINDS = [("allocation", "Allocation"), ("status", "Status change"), ("checkpoint", "Checkpoint"), ("note", "Note")]

    trip = models.ForeignKey("data.Trip", on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=20, choices=KINDS)
    status = models.CharField(max_length=20, blank=True)
    place = place_field("Place", blank=True)
    place_label = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=255, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at", "-id"]


class TripPosition(models.Model):
    """A GPS fix sent by the driver's phone. Staff only."""

    trip = models.ForeignKey("data.Trip", on_delete=models.CASCADE, related_name="positions")
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    speed_kmh = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    accuracy_m = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["recorded_at"]
        indexes = [models.Index(fields=["trip", "recorded_at"])]
