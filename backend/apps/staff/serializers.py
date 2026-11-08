from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import serializers

from apps.data.models import (
    BASIS_FOR_MODE,
    ContactMessage,
    Shipment,
    ShipmentStatus,
    ShippingMode,
    ShippingRate,
    TrackingEvent,
    Trip,
)
from apps.shipments.serializers import ShipmentDetailSerializer, ShipmentListSerializer

User = get_user_model()


def money_field(**kw):
    return serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False, **kw)


# --------------------------------------------------------------------------- shipments

class OwnerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["customer_code", "email", "full_name", "phone"]
        read_only_fields = fields


class StaffEventSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrackingEvent
        fields = ["id", "status", "status_display", "location", "note", "created_at", "created_by_name"]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        return (obj.created_by.get_full_name() or obj.created_by.email) if obj.created_by_id else None


class StaffShipmentListSerializer(ShipmentListSerializer):
    owner = OwnerSerializer(read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    trip_code = serializers.CharField(source="trip.code", read_only=True, default=None)

    class Meta(ShipmentListSerializer.Meta):
        fields = ShipmentListSerializer.Meta.fields + ["owner", "trip_code", "weight_kg", "volume_cbm", "declared_weight_kg",
                                                       "payment_status_display", "pickup_date"]
        read_only_fields = fields


class StaffShipmentDetailSerializer(ShipmentDetailSerializer):
    owner = OwnerSerializer(read_only=True)
    events = StaffEventSerializer(many=True, read_only=True)

    trip_code = serializers.CharField(source="trip.code", read_only=True, default=None)

    class Meta(ShipmentDetailSerializer.Meta):
        fields = ShipmentDetailSerializer.Meta.fields + ["owner", "trip_code", "internal_notes"]
        read_only_fields = fields


class StaffShipmentUpdateSerializer(serializers.ModelSerializer):
    """Fields staff may edit. Status changes go through StatusChangeSerializer
    so every change leaves a tracking event."""

    trip = serializers.SlugRelatedField(slug_field="code", queryset=Trip.objects.all(), allow_null=True, required=False)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False)
    volume_cbm = serializers.DecimalField(max_digits=8, decimal_places=3, min_value=Decimal("0"), allow_null=True, required=False)
    charge_usd = money_field()
    declared_value_usd = money_field()
    internal_notes = serializers.CharField(max_length=2000, allow_blank=True, required=False)

    class Meta:
        model = Shipment
        fields = [
            "trip", "weight_kg", "volume_cbm", "packages_received", "charge_usd", "payment_status", "eta_date",
            "internal_notes", "description", "category", "mode", "service_type", "quantity", "declared_weight_kg",
            "declared_value_usd", "is_hazardous", "is_fragile", "origin", "destination", "pickup_address", "pickup_date",
            "consignee_name", "consignee_phone", "delivery_option", "delivery_address",
        ]

    def validate_trip(self, trip):
        from apps.data.models import TRIP_OPEN_STATUSES

        if trip is not None and trip != getattr(self.instance, "trip", None) and trip.status not in TRIP_OPEN_STATUSES:
            raise serializers.ValidationError("That trip has already left and is not taking cargo.")
        return trip


class SplitSerializer(serializers.Serializer):
    """Move some packages (and their measured weight/volume/charge) into a new part."""

    packages = serializers.IntegerField(min_value=1)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)
    volume_cbm = serializers.DecimalField(max_digits=8, decimal_places=3, min_value=Decimal("0"), required=False, allow_null=True)
    charge_usd = money_field()
    mode = serializers.ChoiceField(choices=ShippingMode.choices, required=False)
    trip = serializers.SlugRelatedField(slug_field="code", queryset=Trip.objects.all(), allow_null=True, required=False)


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ShipmentStatus.choices)
    location = serializers.CharField(max_length=120, allow_blank=True, required=False, default="")
    note = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")


class BulkStatusSerializer(StatusChangeSerializer):
    tracking_numbers = serializers.ListField(child=serializers.CharField(max_length=16), min_length=1, max_length=200)


# --------------------------------------------------------------------------- users

class StaffUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    shipment_count = serializers.IntegerField(read_only=True, default=0)
    active_shipment_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = [
            "customer_code", "email", "first_name", "last_name", "full_name", "phone",
            "is_active", "is_staff", "is_superuser", "is_driver", "licence_number", "date_joined", "last_login",
            "shipment_count", "active_shipment_count",
        ]
        read_only_fields = ["customer_code", "full_name", "is_staff", "is_superuser", "date_joined", "last_login"]
        extra_kwargs = {
            "first_name": {"max_length": 80, "allow_blank": False},
            "last_name": {"max_length": 80, "allow_blank": False},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Another account already uses this email.")
        return value


# --------------------------------------------------------------------------- rates

class StaffRateSerializer(serializers.ModelSerializer):
    """Create and edit pricing plans. `code` and `mode` are fixed once created
    (the code appears in URLs and saved estimates); basis follows the mode."""

    code = serializers.SlugField(max_length=40, required=False)
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    basis_display = serializers.CharField(source="get_basis_display", read_only=True)
    route_display = serializers.CharField(read_only=True)

    class Meta:
        model = ShippingRate
        fields = [
            "code", "name", "mode", "mode_display", "basis", "basis_display", "origin", "destination", "route_display",
            "price_usd", "min_charge_usd",
            "transit_days_min", "transit_days_max", "summary", "best_for", "is_active", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["mode_display", "basis", "basis_display", "created_at", "updated_at"]

    def validate(self, attrs):
        if self.instance is not None:
            for fixed in ("code", "mode"):
                if fixed in attrs and attrs[fixed] != getattr(self.instance, fixed):
                    raise serializers.ValidationError({fixed: "Cannot be changed after the plan is created. Add a new plan instead."})
        else:
            if not attrs.get("code"):
                base = slugify(attrs.get("name", ""))[:34] or "plan"
                code, n = base, 2
                while ShippingRate.objects.filter(code=code).exists():
                    code, n = f"{base}-{n}", n + 1
                attrs["code"] = code
            elif ShippingRate.objects.filter(code=attrs["code"]).exists():
                raise serializers.ValidationError({"code": "A plan with this code already exists."})
        lo = attrs.get("transit_days_min", getattr(self.instance, "transit_days_min", None))
        hi = attrs.get("transit_days_max", getattr(self.instance, "transit_days_max", None))
        if lo is not None and hi is not None and lo > hi:
            raise serializers.ValidationError({"transit_days_max": "Must be at least the minimum transit days."})
        return attrs

    def create(self, validated_data):
        validated_data["basis"] = BASIS_FOR_MODE[validated_data["mode"]]
        if "sort_order" not in validated_data:  # new plans go to the end of the card
            last = ShippingRate.objects.order_by("-sort_order").values_list("sort_order", flat=True).first()
            validated_data["sort_order"] = (last or 0) + 1
        return super().create(validated_data)


# --------------------------------------------------------------------------- fleet

class AllocateSerializer(serializers.Serializer):
    driver = serializers.SlugRelatedField(slug_field="customer_code", queryset=User.objects.filter(is_driver=True, is_active=True))
    truck_id = serializers.IntegerField(required=False, allow_null=True)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class TripFromEmptyLegSerializer(serializers.Serializer):
    departure_date = serializers.DateField(required=False, allow_null=True)
    eta_date = serializers.DateField(required=False, allow_null=True)
    allocate = serializers.BooleanField(default=True, help_text="Allocate the trip to the offering driver straight away.")


# --------------------------------------------------------------------------- messages

class StaffMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "phone", "subject", "message", "created_at", "handled"]
        read_only_fields = ["id", "name", "email", "phone", "subject", "message", "created_at"]
