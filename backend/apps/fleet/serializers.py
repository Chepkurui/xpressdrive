"""Serializers for trips, trucks, empty legs and GPS positions.

Used by the driver app (apps.fleet.views) and the staff portal (apps.staff).
Never used by customer endpoints: these carry driver identity and coordinates.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.data.models import (
    DRIVER_NEXT_STATUS,
    PLACE_CHOICES,
    EmptyLeg,
    Shipment,
    Trip,
    TripEvent,
    TripPosition,
    TripStatus,
    Truck,
    place_name,
)

User = get_user_model()


def _dec(max_digits, places, **kw):
    return serializers.DecimalField(max_digits=max_digits, decimal_places=places, min_value=Decimal("0"),
                                    allow_null=True, required=False, **kw)


class PersonSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["customer_code", "full_name", "phone"]
        read_only_fields = fields


class TruckSerializer(serializers.ModelSerializer):
    truck_type_display = serializers.CharField(source="get_truck_type_display", read_only=True)
    home_base_name = serializers.SerializerMethodField()
    default_driver = serializers.SlugRelatedField(
        slug_field="customer_code", queryset=User.objects.filter(is_driver=True, is_active=True), allow_null=True, required=False
    )
    default_driver_detail = PersonSerializer(source="default_driver", read_only=True)
    capacity_kg = _dec(10, 2)
    capacity_cbm = _dec(8, 3)

    class Meta:
        model = Truck
        fields = [
            "id", "plate_number", "trailer_plate", "truck_type", "truck_type_display", "make_model", "capacity_kg",
            "capacity_cbm", "home_base", "home_base_name", "default_driver", "default_driver_detail", "owner_name",
            "owner_phone", "is_active", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_home_base_name(self, obj):
        return place_name(obj.home_base)

    def validate_plate_number(self, value):
        value = " ".join(value.upper().split())
        if Truck.objects.filter(plate_number=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("A truck with this plate is already registered.")
        return value


class TruckBriefSerializer(serializers.ModelSerializer):
    truck_type_display = serializers.CharField(source="get_truck_type_display", read_only=True)

    class Meta:
        model = Truck
        fields = ["id", "plate_number", "trailer_plate", "truck_type", "truck_type_display", "capacity_kg", "capacity_cbm"]
        read_only_fields = fields


class TripEventSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TripEvent
        fields = ["id", "kind", "kind_display", "status", "status_display", "place", "place_label", "note", "lat", "lng",
                  "created_at", "created_by_name"]
        read_only_fields = fields

    def get_status_display(self, obj):
        return TripStatus(obj.status).label if obj.status in TripStatus.values else obj.status

    def get_created_by_name(self, obj):
        return (obj.created_by.get_full_name() or obj.created_by.email) if obj.created_by_id else None


class LastPositionMixin(serializers.Serializer):
    last_position = serializers.SerializerMethodField()

    def get_last_position(self, obj):
        if obj.last_lat is None:
            return None
        return {"lat": float(obj.last_lat), "lng": float(obj.last_lng), "speed_kmh": obj.last_speed_kmh,
                "heading": obj.last_heading, "at": obj.last_position_at}


class TripSerializer(LastPositionMixin, serializers.ModelSerializer):
    """Staff view of a trip (list + edit). Driver/truck are set by code/plate."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    origin_name = serializers.CharField(read_only=True)
    destination_name = serializers.CharField(read_only=True)
    driver_response_display = serializers.CharField(source="get_driver_response_display", read_only=True)
    driver = PersonSerializer(read_only=True)
    truck = TruckBriefSerializer(read_only=True)
    truck_id = serializers.PrimaryKeyRelatedField(source="truck", queryset=Truck.objects.filter(is_active=True),
                                                  allow_null=True, required=False, write_only=True)
    shipment_count = serializers.IntegerField(read_only=True, default=0)
    used_cbm = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True, default=0)
    used_kg = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, default=0)
    capacity_cbm = _dec(8, 3)
    capacity_kg = _dec(10, 2)
    empty_leg_id = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "code", "status", "status_display", "origin", "origin_name", "destination", "destination_name", "is_backhaul",
            "driver", "truck", "truck_id", "driver_response", "driver_response_display", "decline_reason",
            "capacity_cbm", "capacity_kg", "carrier_reference", "departure_date", "eta_date", "notes", "created_at",
            "allocated_at", "responded_at", "started_at", "completed_at", "last_position",
            "shipment_count", "used_cbm", "used_kg", "empty_leg_id",
        ]
        read_only_fields = ["code", "status", "created_at", "driver_response", "decline_reason", "allocated_at",
                            "responded_at", "started_at", "completed_at"]

    def get_empty_leg_id(self, obj):
        leg = getattr(obj, "empty_leg", None) if hasattr(obj, "empty_leg") else None
        return leg.pk if leg else None

    def validate(self, attrs):
        origin = attrs.get("origin", getattr(self.instance, "origin", None))
        destination = attrs.get("destination", getattr(self.instance, "destination", None))
        if origin and destination and origin == destination:
            raise serializers.ValidationError({"destination": "Must differ from the origin."})
        truck = attrs.get("truck")
        if truck is not None and not self.instance:
            attrs.setdefault("capacity_kg", truck.capacity_kg)
            attrs.setdefault("capacity_cbm", truck.capacity_cbm)
        return attrs


class DriverConsignmentSerializer(serializers.ModelSerializer):
    """What a driver needs to load and hand over cargo. No prices."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    origin_name = serializers.CharField(read_only=True)
    destination_name = serializers.CharField(read_only=True)
    shipper = PersonSerializer(source="owner", read_only=True)
    delivery_option_display = serializers.CharField(source="get_delivery_option_display", read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "tracking_number", "description", "mode", "mode_display", "quantity", "packages_received", "weight_kg",
            "volume_cbm", "declared_weight_kg", "is_fragile", "is_hazardous", "status", "status_display",
            "origin_name", "destination_name", "pickup_address", "pickup_date", "shipper",
            "consignee_name", "consignee_phone", "delivery_option", "delivery_option_display", "delivery_address",
        ]
        read_only_fields = fields


class DriverTripSerializer(LastPositionMixin, serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    origin_name = serializers.CharField(read_only=True)
    destination_name = serializers.CharField(read_only=True)
    truck = TruckBriefSerializer(read_only=True)
    shipment_count = serializers.SerializerMethodField()
    next_statuses = serializers.SerializerMethodField()
    is_live = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "code", "status", "status_display", "origin", "origin_name", "destination", "destination_name", "is_backhaul",
            "truck", "driver_response", "capacity_cbm", "capacity_kg", "carrier_reference", "departure_date", "eta_date",
            "notes", "allocated_at", "started_at", "completed_at", "last_position", "shipment_count", "next_statuses", "is_live",
        ]
        read_only_fields = fields

    def get_shipment_count(self, obj):
        n = getattr(obj, "shipment_count", None)
        return n if n is not None else obj.shipments.count()

    def get_next_statuses(self, obj):
        return [{"status": s.value, "label": s.label} for s in DRIVER_NEXT_STATUS.get(obj.status, [])]

    def get_is_live(self, obj):
        from apps.data.models import TRIP_LIVE_STATUSES

        return obj.status in TRIP_LIVE_STATUSES


class DriverTripDetailSerializer(DriverTripSerializer):
    consignments = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()

    class Meta(DriverTripSerializer.Meta):
        fields = DriverTripSerializer.Meta.fields + ["consignments", "events"]
        read_only_fields = fields

    def get_consignments(self, obj):
        qs = obj.shipments.exclude(status="cancelled").select_related("owner")
        return DriverConsignmentSerializer(qs, many=True).data

    def get_events(self, obj):
        return TripEventSerializer(obj.events.select_related("created_by")[:30], many=True).data


class RespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class _PlaceMixin(serializers.Serializer):
    place = serializers.ChoiceField(choices=PLACE_CHOICES, required=False, allow_blank=True, default="")
    place_label = serializers.CharField(max_length=120, required=False, allow_blank=True, default="",
                                        help_text="Free-text place name if not in the list, e.g. 'Lukaya weighbridge'.")
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=Decimal("-90"), max_value=Decimal("90"),
                                   required=False, allow_null=True, default=None)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=Decimal("-180"), max_value=Decimal("180"),
                                   required=False, allow_null=True, default=None)

    def to_internal_value(self, data):
        # Phones send full-precision floats; store to ~0.1 m.
        if hasattr(data, "copy"):
            data = data.copy()
            for k in ("lat", "lng"):
                if isinstance(data.get(k), float):
                    data[k] = round(data[k], 6)
        return super().to_internal_value(data)


class CheckpointSerializer(_PlaceMixin):
    def validate(self, attrs):
        if not (attrs["place"] or attrs["place_label"].strip()):
            raise serializers.ValidationError({"place": "Choose a place or type its name."})
        return attrs


class TripMoveSerializer(_PlaceMixin):
    status = serializers.ChoiceField(choices=TripStatus.choices)


class PositionSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    speed_kmh = serializers.FloatField(min_value=0, max_value=300, required=False, allow_null=True)
    heading = serializers.FloatField(min_value=0, max_value=360, required=False, allow_null=True)
    accuracy_m = serializers.FloatField(min_value=0, max_value=100000, required=False, allow_null=True)
    recorded_at = serializers.DateTimeField()

    def validate_recorded_at(self, value):
        now = timezone.now()
        if value > now + timedelta(minutes=5):
            raise serializers.ValidationError("Time is in the future; check the phone's clock.")
        if value < now - timedelta(days=7):
            raise serializers.ValidationError("Position is too old.")
        return value


class PositionBatchSerializer(serializers.Serializer):
    positions = PositionSerializer(many=True, allow_empty=False, max_length=200)


class TripPositionSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()

    class Meta:
        model = TripPosition
        fields = ["lat", "lng", "speed_kmh", "heading", "accuracy_m", "recorded_at"]
        read_only_fields = fields


class EmptyLegSerializer(serializers.ModelSerializer):
    """Drivers create/edit their own; staff see all and convert them to trips."""

    origin_name = serializers.SerializerMethodField()
    destination_name = serializers.SerializerMethodField()
    space_display = serializers.CharField(source="get_space_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    driver = PersonSerializer(read_only=True)
    truck = TruckBriefSerializer(read_only=True)
    truck_id = serializers.PrimaryKeyRelatedField(source="truck", queryset=Truck.objects.filter(is_active=True),
                                                  allow_null=True, required=False, write_only=True)
    trip_code = serializers.CharField(source="trip.code", read_only=True, default=None)
    capacity_kg = _dec(10, 2)
    capacity_cbm = _dec(8, 3)

    class Meta:
        model = EmptyLeg
        fields = [
            "id", "origin", "origin_name", "destination", "destination_name", "available_from", "available_until",
            "space", "space_display", "capacity_kg", "capacity_cbm", "vehicle_description", "notes",
            "status", "status_display", "driver", "truck", "truck_id", "trip_code", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_origin_name(self, obj):
        return place_name(obj.origin)

    def get_destination_name(self, obj):
        return place_name(obj.destination)

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731
        if get("origin") == get("destination"):
            raise serializers.ValidationError({"destination": "Must differ from where you are starting."})
        if get("available_until") and get("available_from") and get("available_until") < get("available_from"):
            raise serializers.ValidationError({"available_until": "Must be on or after the start date."})
        if not self.instance and get("available_from") and get("available_from") < timezone.localdate() - timedelta(days=1):
            raise serializers.ValidationError({"available_from": "Choose today or a later date."})
        return attrs


class PublicCapacitySerializer(serializers.Serializer):
    """Open return-truck space for the public board. Lane, date and space only:
    no driver, truck or plate."""

    origin = serializers.CharField()
    origin_name = serializers.CharField()
    destination = serializers.CharField()
    destination_name = serializers.CharField()
    date_from = serializers.DateField(allow_null=True)
    date_to = serializers.DateField(allow_null=True)
    space = serializers.CharField()
    space_display = serializers.CharField()
