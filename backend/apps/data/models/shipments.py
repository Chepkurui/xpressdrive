import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from .places import place_field, place_name
from .pricing import ShippingMode

TRACKING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity
TRACKING_PREFIX = "XD"
TRACKING_LENGTH = 10  # 32^10 ≈ 1.1e15 combinations: not guessable


def generate_tracking_number():
    return TRACKING_PREFIX + "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(TRACKING_LENGTH))


class ShipmentStatus(models.TextChoices):
    """Milestones a cargo owner sees. Never includes live coordinates."""

    BOOKED = "booked", "Booking received"
    CONFIRMED = "confirmed", "Confirmed — awaiting truck"
    ALLOCATED = "allocated", "Truck allocated"
    LOADED = "loaded", "Loaded at origin"
    IN_TRANSIT = "in_transit", "In transit"
    AT_BORDER = "at_border", "At border / customs"
    ARRIVED = "arrived", "Arrived at destination"
    DELIVERED = "delivered", "Delivered"
    ON_HOLD = "on_hold", "On hold"
    CANCELLED = "cancelled", "Cancelled"


ACTIVE_STATUSES = [
    ShipmentStatus.BOOKED,
    ShipmentStatus.CONFIRMED,
    ShipmentStatus.ALLOCATED,
    ShipmentStatus.LOADED,
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.AT_BORDER,
    ShipmentStatus.ARRIVED,
    ShipmentStatus.ON_HOLD,
]
CLOSED_STATUSES = [ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED]


class Category(models.TextChoices):
    GENERAL = "general", "General goods"
    FMCG = "fmcg", "Food, drinks & FMCG"
    AGRICULTURE = "agriculture", "Agricultural produce"
    ELECTRONICS = "electronics", "Electronics & phones"
    CLOTHING = "clothing", "Clothing, shoes & bags"
    HOME = "home", "Home, kitchen & furniture"
    MACHINERY = "machinery", "Machinery & spare parts"
    BUILDING = "building", "Building & hardware"
    OTHER = "other", "Other"


class ServiceType(models.TextChoices):
    CONSOLIDATED = "consolidated", "Shared truck (consolidated)"
    DEDICATED = "dedicated", "Dedicated truck"


class DeliveryOption(models.TextChoices):
    PICKUP = "pickup", "Collect at destination depot"
    DELIVERY = "delivery", "Deliver to receiver's address"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Awaiting quote"
    UNPAID = "unpaid", "Unpaid"
    PAID = "paid", "Paid"
    WAIVED = "waived", "Waived"


class TripStatus(models.TextChoices):
    PLANNED = "planned", "Planned — accepting cargo"
    ALLOCATED = "allocated", "Allocated — awaiting driver"
    ACCEPTED = "accepted", "Accepted by driver"
    LOADING = "loading", "Loading at origin"
    IN_TRANSIT = "in_transit", "In transit"
    AT_BORDER = "at_border", "At border / customs"
    ARRIVED = "arrived", "Arrived at destination"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class DriverResponse(models.TextChoices):
    PENDING = "pending", "Awaiting response"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"


# Status a trip move implies for every open consignment on it.
TRIP_TO_SHIPMENT_STATUS = {
    TripStatus.ACCEPTED: ShipmentStatus.ALLOCATED,
    TripStatus.LOADING: ShipmentStatus.LOADED,
    TripStatus.IN_TRANSIT: ShipmentStatus.IN_TRANSIT,
    TripStatus.AT_BORDER: ShipmentStatus.AT_BORDER,
    TripStatus.ARRIVED: ShipmentStatus.ARRIVED,
}
# Trip stages during which the driver's phone shares its position.
TRIP_LIVE_STATUSES = [TripStatus.ACCEPTED, TripStatus.LOADING, TripStatus.IN_TRANSIT, TripStatus.AT_BORDER, TripStatus.ARRIVED]
# Stages in which cargo can still be added to a trip.
TRIP_OPEN_STATUSES = [TripStatus.PLANNED, TripStatus.ALLOCATED, TripStatus.ACCEPTED, TripStatus.LOADING]
# What the driver may do next from each stage.
DRIVER_NEXT_STATUS = {
    TripStatus.ACCEPTED: [TripStatus.LOADING],
    TripStatus.LOADING: [TripStatus.IN_TRANSIT],
    TripStatus.IN_TRANSIT: [TripStatus.AT_BORDER, TripStatus.ARRIVED],
    TripStatus.AT_BORDER: [TripStatus.IN_TRANSIT, TripStatus.ARRIVED],
    TripStatus.ARRIVED: [TripStatus.COMPLETED],
}


def generate_trip_code():
    return "XT" + timezone.now().strftime("%y%m") + "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(4))


class Trip(models.Model):
    """One truck journey on one lane, carrying one or many customers' cargo.

    Often a backhaul: a truck or empty container returning to base, filled with
    cargo going the same way. Admins allocate it to a driver, who accepts it in
    the mobile app and shares the truck's position while it is under way.
    """

    code = models.CharField(max_length=20, unique=True, default=generate_trip_code)
    status = models.CharField(max_length=20, choices=TripStatus.choices, default=TripStatus.PLANNED, db_index=True)
    origin = place_field("From")
    destination = place_field("To")
    is_backhaul = models.BooleanField("Return / backhaul leg", default=False,
                                      help_text="Truck or empty container returning to base.")
    truck = models.ForeignKey("data.Truck", on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="trips", limit_choices_to={"is_driver": True})
    capacity_cbm = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carrier_reference = models.CharField("Container no. / reference", max_length=80, blank=True)
    departure_date = models.DateField(null=True, blank=True)
    eta_date = models.DateField("ETA destination", null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Staff and driver only.")
    created_at = models.DateTimeField(auto_now_add=True)

    # Allocation
    driver_response = models.CharField(max_length=20, choices=DriverResponse.choices, blank=True)
    decline_reason = models.CharField(max_length=255, blank=True)
    allocated_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Last known position (staff only — never shown to cargo owners)
    last_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_speed_kmh = models.FloatField(null=True, blank=True)
    last_heading = models.FloatField(null=True, blank=True)
    last_position_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.origin_name} → {self.destination_name})"

    @property
    def origin_name(self):
        return place_name(self.origin)

    @property
    def destination_name(self):
        return place_name(self.destination)

    def used_cbm(self):
        return self.shipments.aggregate(total=models.Sum("volume_cbm"))["total"] or Decimal("0")

    def used_kg(self):
        return self.shipments.aggregate(total=models.Sum("weight_kg"))["total"] or Decimal("0")

    # ------------------------------------------------------------------ workflow
    def log(self, kind, *, status="", place="", place_label="", note="", user=None, lat=None, lng=None):
        from .fleet import TripEvent

        return TripEvent.objects.create(
            trip=self, kind=kind, status=status, place=place, place_label=place_label[:120], note=note[:255],
            lat=lat, lng=lng, created_by=user,
        )

    @transaction.atomic
    def apply_shipment_status(self, status, location="", note="", user=None):
        count = 0
        for shipment in self.shipments.exclude(status__in=CLOSED_STATUSES).select_for_update():
            shipment.update_status(status, location=location, note=note, user=user, eta=self.eta_date)
            count += 1
        return count

    @transaction.atomic
    def allocate(self, driver, truck=None, user=None, note=""):
        self.driver = driver
        if truck is not None:
            self.truck = truck
            self.capacity_kg = self.capacity_kg or truck.capacity_kg
            self.capacity_cbm = self.capacity_cbm or truck.capacity_cbm
        self.status = TripStatus.ALLOCATED
        self.driver_response = DriverResponse.PENDING
        self.decline_reason = ""
        self.allocated_at = timezone.now()
        self.responded_at = None
        self.save()
        who = driver.get_full_name() or driver.email
        self.log("allocation", status=self.status, note=note or f"Allocated to {who}.", user=user)

    @transaction.atomic
    def respond(self, accept, reason="", user=None):
        self.responded_at = timezone.now()
        if accept:
            self.driver_response = DriverResponse.ACCEPTED
            self.status = TripStatus.ACCEPTED
            self.save()
            self.log("allocation", status=self.status, note="Driver accepted the trip.", user=user)
            self.apply_shipment_status(ShipmentStatus.ALLOCATED, user=user)
        else:
            who = self.driver.get_full_name() if self.driver_id else "Driver"
            self.driver_response = DriverResponse.DECLINED
            self.decline_reason = reason[:255]
            self.status = TripStatus.PLANNED
            self.driver = None
            self.save()
            self.log("allocation", status=self.status, note=f"{who} declined{': ' + reason if reason else ''}"[:255], user=user)

    @transaction.atomic
    def advance(self, status, *, place="", place_label="", note="", user=None, lat=None, lng=None):
        """Move the trip to `status` and every open consignment on it to the matching milestone.
        Cargo owners see the place name (if any) and the note; never coordinates."""
        now = timezone.now()
        self.status = status
        if status == TripStatus.IN_TRANSIT and not self.started_at:
            self.started_at = now
        if status in (TripStatus.COMPLETED, TripStatus.CANCELLED):
            self.completed_at = now
        self.save()
        self.log("status", status=status, place=place, place_label=place_label, note=note, user=user, lat=lat, lng=lng)
        target = TRIP_TO_SHIPMENT_STATUS.get(status)
        if target:
            return self.apply_shipment_status(target, location=place_label or place_name(place), note=note, user=user)
        return 0

    @transaction.atomic
    def checkpoint(self, *, place="", place_label="", note="", user=None, lat=None, lng=None):
        """A major point reached on the road (town, weighbridge, border). Adds a
        milestone to each consignment's timeline without changing its status."""
        label = place_label or place_name(place)
        self.log("checkpoint", status=self.status, place=place, place_label=label, note=note, user=user, lat=lat, lng=lng)
        count = 0
        for shipment in self.shipments.exclude(status__in=CLOSED_STATUSES):
            TrackingEvent.objects.create(shipment=shipment, status=shipment.status, location=label, note=note, created_by=user)
            count += 1
        return count


class Shipment(models.Model):
    """One customer's cargo booking (a "consignment"): anything from a parcel to a full container."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_number = models.CharField(max_length=16, unique=True, editable=False, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="shipments")
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True, related_name="shipments")
    # A customer's cargo can be split across trucks (e.g. 12 pallets on this
    # truck, 8 on the next). Each part is a Shipment of its own, owned by the
    # same customer and pointing at the ORIGINAL booking, so parts never nest.
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="parts",
        help_text="Set on parts split off another booking.", verbose_name="original booking",
    )

    # Route
    origin = place_field("From")
    destination = place_field("To")
    pickup_address = models.CharField(max_length=255, blank=True)
    pickup_date = models.DateField("Ready for pickup on", null=True, blank=True)

    # Declared by the customer
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    mode = models.CharField("Load type", max_length=20, choices=ShippingMode.choices, default=ShippingMode.PART_LOAD)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices, default=ServiceType.CONSOLIDATED)
    quantity = models.PositiveIntegerField("Packages / pallets", default=1, validators=[MinValueValidator(1)])
    declared_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    declared_value_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_hazardous = models.BooleanField(default=False)
    is_fragile = models.BooleanField(default=False)
    consignee_name = models.CharField("Receiver name", max_length=120, blank=True)
    consignee_phone = models.CharField("Receiver phone", max_length=30, blank=True)
    delivery_option = models.CharField(max_length=20, choices=DeliveryOption.choices, default=DeliveryOption.PICKUP)
    delivery_address = models.CharField(max_length=255, blank=True)
    customer_notes = models.TextField(blank=True)

    # Set by staff
    status = models.CharField(max_length=20, choices=ShipmentStatus.choices, default=ShipmentStatus.BOOKED, db_index=True)
    weight_kg = models.DecimalField("Measured weight (kg)", max_digits=10, decimal_places=2, null=True, blank=True)
    volume_cbm = models.DecimalField("Measured volume (CBM)", max_digits=8, decimal_places=3, null=True, blank=True)
    packages_received = models.PositiveIntegerField(null=True, blank=True)
    charge_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    eta_date = models.DateField("ETA destination", null=True, blank=True)
    internal_notes = models.TextField(blank=True, help_text="Staff only, never shown to customers.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    received_at = models.DateTimeField("Loaded at", null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"])]
        verbose_name = "booking"
        verbose_name_plural = "bookings"

    def __str__(self):
        return f"{self.tracking_number} — {self.description[:40]}"

    @property
    def origin_name(self):
        return place_name(self.origin)

    @property
    def destination_name(self):
        return place_name(self.destination)

    @property
    def is_editable_by_customer(self):
        return self.status == ShipmentStatus.BOOKED

    def default_location(self, status):
        if status in (ShipmentStatus.CONFIRMED, ShipmentStatus.ALLOCATED, ShipmentStatus.LOADED):
            return self.origin_name
        if status in (ShipmentStatus.ARRIVED, ShipmentStatus.DELIVERED):
            return self.destination_name
        return ""

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.tracking_number:
            number = generate_tracking_number()
            while Shipment.objects.filter(tracking_number=number).exists():
                number = generate_tracking_number()
            self.tracking_number = number
        super().save(*args, **kwargs)
        if is_new:
            if getattr(self, "_skip_initial_event", False):
                return
            TrackingEvent.objects.create(
                shipment=self, status=self.status, location=self.origin_name, note="Booking received.",
            )

    # ------------------------------------------------------------------ parts
    SPLITTABLE_STATUSES = (ShipmentStatus.CONFIRMED, ShipmentStatus.ALLOCATED)

    @property
    def root(self):
        return self.parent or self

    def group(self):
        """The original booking followed by its parts, oldest first."""
        root = self.root
        # .all() + Python sort so a prefetch of parent/parts is reused (no N+1 in lists)
        return [root, *sorted(root.parts.all(), key=lambda s: (s.created_at, str(s.pk)))]

    @transaction.atomic
    def split(self, *, packages, weight_kg=None, volume_cbm=None, charge_usd=None, mode=None, trip=None, user=None):
        """Move some of this booking's cargo into a new part (same customer) so
        it can travel on another truck.

        Measurements and charge are moved, not copied, so trip fill levels and
        the customer's total stay correct. The part inherits the tracking history
        so far and then moves independently (its own trip, status and ETA).
        """
        from django.core.exceptions import ValidationError

        locked = Shipment.objects.select_for_update().get(pk=self.pk)
        if locked.status not in self.SPLITTABLE_STATUSES:
            raise ValidationError("Only cargo that has not been loaded yet (confirmed or truck allocated) can be split.")
        have = locked.packages_received or locked.quantity
        if not 0 < packages < have:
            raise ValidationError({"packages": f"Move between 1 and {have - 1} of the {have} packages."})

        def take(field, amount):
            if amount is None:
                return None
            current = getattr(locked, field)
            if current is None or not Decimal("0") <= amount <= current:
                raise ValidationError({field: f"Can be at most the booking's current value ({current or 0})."})
            setattr(locked, field, current - amount)
            return amount

        if trip is not None and trip.status not in TRIP_OPEN_STATUSES:
            raise ValidationError({"trip": "That trip is no longer taking cargo."})

        part = Shipment(
            owner=locked.owner, parent=locked.root, trip=trip, mode=mode or locked.mode, status=locked.status,
            origin=locked.origin, destination=locked.destination, pickup_address=locked.pickup_address,
            pickup_date=locked.pickup_date,
            description=locked.description, category=locked.category, service_type=locked.service_type,
            quantity=packages, packages_received=packages,
            consignee_name=locked.consignee_name, consignee_phone=locked.consignee_phone,
            is_hazardous=locked.is_hazardous, is_fragile=locked.is_fragile,
            delivery_option=locked.delivery_option, delivery_address=locked.delivery_address,
            customer_notes=locked.customer_notes, received_at=locked.received_at,
            weight_kg=take("weight_kg", weight_kg), volume_cbm=take("volume_cbm", volume_cbm),
            charge_usd=take("charge_usd", charge_usd),
        )
        part.payment_status = (
            locked.payment_status
            if part.charge_usd is not None or locked.payment_status in (PaymentStatus.PAID, PaymentStatus.WAIVED)
            else PaymentStatus.PENDING
        )
        locked.packages_received = have - packages
        part._skip_initial_event = True
        part.save()
        locked.save(update_fields=["packages_received", "weight_kg", "volume_cbm", "charge_usd", "updated_at"])

        # The part's timeline starts with the history so far, then the split.
        TrackingEvent.objects.bulk_create([
            TrackingEvent(shipment=part, status=e.status, location=e.location, note=e.note, created_at=e.created_at, created_by=e.created_by)
            for e in locked.events.order_by("created_at", "id")
        ])
        TrackingEvent.objects.create(
            shipment=part, status=part.status, location=part.origin_name,
            note=f"{packages} package(s) split off from {locked.tracking_number} to travel on another truck.", created_by=user,
        )
        TrackingEvent.objects.create(
            shipment=locked, status=locked.status, location=locked.origin_name,
            note=f"{packages} package(s) moved to {part.tracking_number}, which will travel on another truck.", created_by=user,
        )
        self.refresh_from_db()
        return part

    def update_status(self, status, location="", note="", user=None, eta=None):
        now = timezone.now()
        self.status = status
        fields = ["status", "updated_at"]
        if status == ShipmentStatus.LOADED and not self.received_at:
            self.received_at = now
            fields.append("received_at")
        if status == ShipmentStatus.DELIVERED:
            self.delivered_at = now
            fields.append("delivered_at")
        if eta and not self.eta_date:
            self.eta_date = eta
            fields.append("eta_date")
        self.save(update_fields=fields)
        return TrackingEvent.objects.create(
            shipment=self,
            status=status,
            location=location or self.default_location(status),
            note=note,
            created_by=user,
        )


class TrackingEvent(models.Model):
    """A milestone on a booking's timeline, visible to its owner: a status and
    a place *name* (town, border post) — never GPS coordinates."""

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20, choices=ShipmentStatus.choices)
    location = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=255, blank=True, help_text="Visible to the customer.")
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.shipment.tracking_number}: {self.get_status_display()}"


def generate_batch_code():
    """Kept so migration 0001 (which predates trips) still imports."""
    return generate_trip_code()
