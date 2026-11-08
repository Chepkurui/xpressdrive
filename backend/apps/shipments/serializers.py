from decimal import Decimal

from rest_framework import serializers

from apps.data.models import Shipment, TrackingEvent

# Cargo owners see milestones by place name only. Nothing in this module may
# expose a trip, driver, truck or coordinates.


class TrackingEventSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TrackingEvent
        fields = ["status", "status_display", "location", "note", "created_at"]


class PublicTrackingEventSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TrackingEvent
        fields = ["status", "status_display", "location", "created_at"]


class ShipmentListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    origin_name = serializers.CharField(read_only=True)
    destination_name = serializers.CharField(read_only=True)
    part = serializers.SerializerMethodField(help_text="Set when the cargo travels in more than one part.")

    def get_part(self, obj):
        """Where this booking sits among the customer's split parts. Parts always
        share one owner, so this never reveals anyone else's cargo."""
        group = obj.group()
        if len(group) < 2:
            return None
        return {
            "number": next(i for i, s in enumerate(group, 1) if s.pk == obj.pk),
            "count": len(group),
            "original": group[0].tracking_number,
            "siblings": [
                {"tracking_number": s.tracking_number, "status": s.status, "status_display": s.get_status_display(), "eta_date": s.eta_date}
                for s in group if s.pk != obj.pk
            ],
        }

    class Meta:
        model = Shipment
        fields = [
            "tracking_number",
            "description",
            "category",
            "mode",
            "mode_display",
            "service_type",
            "origin",
            "origin_name",
            "destination",
            "destination_name",
            "quantity",
            "status",
            "status_display",
            "charge_usd",
            "payment_status",
            "eta_date",
            "part",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ShipmentDetailSerializer(ShipmentListSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    service_type_display = serializers.CharField(source="get_service_type_display", read_only=True)
    delivery_option_display = serializers.CharField(source="get_delivery_option_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    is_editable = serializers.BooleanField(source="is_editable_by_customer", read_only=True)
    events = TrackingEventSerializer(many=True, read_only=True)

    class Meta(ShipmentListSerializer.Meta):
        fields = ShipmentListSerializer.Meta.fields + [
            "category_display",
            "service_type_display",
            "pickup_address",
            "pickup_date",
            "declared_weight_kg",
            "declared_value_usd",
            "is_hazardous",
            "is_fragile",
            "consignee_name",
            "consignee_phone",
            "delivery_option",
            "delivery_option_display",
            "delivery_address",
            "customer_notes",
            "weight_kg",
            "volume_cbm",
            "packages_received",
            "payment_status_display",
            "received_at",
            "delivered_at",
            "is_editable",
            "events",
        ]
        read_only_fields = fields


class ShipmentWriteSerializer(serializers.ModelSerializer):
    """Customer-writable fields only. Status, charges, measurements, trip and
    owner are set server-side, so they cannot be mass-assigned."""

    description = serializers.CharField(max_length=255, min_length=3)
    quantity = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    declared_weight_kg = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.1"), max_value=Decimal("60000"), required=False, allow_null=True
    )
    declared_value_usd = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("5000000"), required=False, allow_null=True
    )
    pickup_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    consignee_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    consignee_phone = serializers.RegexField(r"^\+?[0-9][0-9 \-]{6,18}$", max_length=30, required=False, allow_blank=True,
                                             error_messages={"invalid": "Enter a valid phone number, e.g. +256 700 000000."})
    customer_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    class Meta:
        model = Shipment
        fields = [
            "origin",
            "destination",
            "pickup_address",
            "pickup_date",
            "description",
            "category",
            "mode",
            "service_type",
            "quantity",
            "declared_weight_kg",
            "declared_value_usd",
            "is_hazardous",
            "is_fragile",
            "consignee_name",
            "consignee_phone",
            "delivery_option",
            "delivery_address",
            "customer_notes",
        ]

    def validate(self, attrs):
        origin = attrs.get("origin", getattr(self.instance, "origin", None))
        destination = attrs.get("destination", getattr(self.instance, "destination", None))
        if origin and destination and origin == destination:
            raise serializers.ValidationError({"destination": "Choose a destination different from the pickup town."})
        option = attrs.get("delivery_option", getattr(self.instance, "delivery_option", None))
        address = attrs.get("delivery_address", getattr(self.instance, "delivery_address", ""))
        if option == "delivery" and not (address or "").strip():
            raise serializers.ValidationError({"delivery_address": "A delivery address is required for door delivery."})
        return attrs


class PublicTrackingSerializer(serializers.ModelSerializer):
    """Minimal, non-personal view for anyone holding a tracking number."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    origin_name = serializers.CharField(read_only=True)
    destination_name = serializers.CharField(read_only=True)
    events = PublicTrackingEventSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = ["tracking_number", "status", "status_display", "mode", "mode_display", "origin_name", "destination_name",
                  "eta_date", "updated_at", "events"]
        read_only_fields = fields
