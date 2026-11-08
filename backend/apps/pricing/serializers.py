from decimal import Decimal

from rest_framework import serializers

from apps.data.models import RateBasis, ShippingMode, ShippingRate


class ShippingRateSerializer(serializers.ModelSerializer):
    mode_display = serializers.CharField(source="get_mode_display", read_only=True)
    basis_display = serializers.CharField(source="get_basis_display", read_only=True)
    route_display = serializers.CharField(read_only=True)

    class Meta:
        model = ShippingRate
        fields = [
            "code",
            "name",
            "mode",
            "mode_display",
            "basis",
            "basis_display",
            "origin",
            "destination",
            "route_display",
            "price_usd",
            "min_charge_usd",
            "transit_days_min",
            "transit_days_max",
            "summary",
            "best_for",
        ]


def _dim():
    return serializers.DecimalField(
        max_digits=7, decimal_places=1, min_value=Decimal("1"), max_value=Decimal("1500"), required=False
    )


class EstimateRequestSerializer(serializers.Serializer):
    plan = serializers.SlugField(max_length=40, required=False, help_text="Pricing plan code (preferred).")
    mode = serializers.ChoiceField(choices=ShippingMode.choices, required=False,
                                   help_text="Used when no plan is given: the first active plan for this load type.")
    weight_kg = serializers.DecimalField(
        max_digits=9, decimal_places=2, min_value=Decimal("0.01"), max_value=Decimal("30000"),
        help_text="Weight of ONE package in kg",
    )
    quantity = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    length_cm = _dim()
    width_cm = _dim()
    height_cm = _dim()
    containers = serializers.IntegerField(min_value=1, max_value=50, default=1, help_text="Trucks / containers, for full loads.")

    def validate(self, attrs):
        dims = [attrs.get(k) for k in ("length_cm", "width_cm", "height_cm")]
        if any(d is not None for d in dims) and not all(d is not None for d in dims):
            raise serializers.ValidationError("Provide length, width and height together.")
        if attrs.get("plan"):
            rate = ShippingRate.objects.filter(code=attrs["plan"], is_active=True).first()
            if rate is None:
                raise serializers.ValidationError({"plan": "This pricing plan is currently unavailable."})
        elif attrs.get("mode"):
            rate = ShippingRate.default_for_mode(attrs["mode"])
            if rate is None:
                raise serializers.ValidationError({"mode": "This load type is currently unavailable."})
        else:
            raise serializers.ValidationError({"plan": "Choose a pricing plan."})
        if rate.basis == RateBasis.PER_CBM and dims[0] is None:
            raise serializers.ValidationError("Package dimensions are required for part-load estimates.")
        attrs["rate"] = rate
        return attrs


class EstimateResponseSerializer(serializers.Serializer):
    plan = serializers.CharField()
    plan_name = serializers.CharField()
    mode = serializers.CharField()
    basis = serializers.CharField()
    actual_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2)
    volumetric_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    volume_cbm = serializers.DecimalField(max_digits=12, decimal_places=3, allow_null=True)
    chargeable_quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    chargeable_unit = serializers.CharField()
    cost_low_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    cost_high_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    transit_days_min = serializers.IntegerField()
    transit_days_max = serializers.IntegerField()
    disclaimer = serializers.CharField()
