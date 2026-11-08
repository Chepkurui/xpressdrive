from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from apps.data.models import RateBasis, ShippingRate

ROAD_VOLUMETRIC_DIVISOR = Decimal("3000")  # road freight: 1 CBM charged as at least 333 kg
CM3_PER_CBM = Decimal("1000000")
TWO_PLACES = Decimal("0.01")
THREE_PLACES = Decimal("0.001")


@dataclass
class Estimate:
    plan: str
    plan_name: str
    mode: str
    basis: str
    actual_weight_kg: Decimal
    volumetric_weight_kg: Decimal | None
    volume_cbm: Decimal | None
    chargeable_quantity: Decimal
    chargeable_unit: str
    cost_low_usd: Decimal
    cost_high_usd: Decimal
    transit_days_min: int
    transit_days_max: int


def calculate_estimate(rate: ShippingRate, *, weight_kg, quantity, length_cm=None, width_cm=None, height_cm=None, containers=1):
    qty = Decimal(quantity)
    actual_weight = (Decimal(weight_kg) * qty).quantize(TWO_PLACES)
    has_dims = all(v is not None for v in (length_cm, width_cm, height_cm))
    cm3 = (Decimal(length_cm) * Decimal(width_cm) * Decimal(height_cm) * qty) if has_dims else None

    volumetric = None
    volume_cbm = (cm3 / CM3_PER_CBM).quantize(THREE_PLACES) if cm3 is not None else None

    if rate.basis == RateBasis.PER_KG:
        volumetric = (cm3 / ROAD_VOLUMETRIC_DIVISOR).quantize(TWO_PLACES) if cm3 is not None else None
        chargeable = max(actual_weight, volumetric or Decimal("0"))
        unit = "kg"
    elif rate.basis == RateBasis.PER_CBM:
        chargeable = volume_cbm
        unit = "cbm"
    else:
        chargeable = Decimal(containers)
        unit = "container"

    cost = max(chargeable * rate.price_usd, rate.min_charge_usd).quantize(TWO_PLACES, ROUND_HALF_UP)
    high = (cost * (Decimal("1") + Decimal(str(settings.ESTIMATE_VARIANCE)))).quantize(TWO_PLACES, ROUND_HALF_UP)

    return Estimate(
        plan=rate.code,
        plan_name=rate.name,
        mode=rate.mode,
        basis=rate.basis,
        actual_weight_kg=actual_weight,
        volumetric_weight_kg=volumetric,
        volume_cbm=volume_cbm,
        chargeable_quantity=chargeable,
        chargeable_unit=unit,
        cost_low_usd=cost,
        cost_high_usd=high,
        transit_days_min=rate.transit_days_min,
        transit_days_max=rate.transit_days_max,
    )
