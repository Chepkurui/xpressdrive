from decimal import Decimal

from django.db import migrations

RATES = [
    dict(mode="air_express", basis="per_kg", price_usd=Decimal("13.00"), min_charge_usd=Decimal("30.00"),
         transit_days_min=5, transit_days_max=8, sort_order=1,
         summary="Fastest door-to-Kampala option for urgent, high-value or small parcels.",
         best_for="Phones, documents, samples, urgent spare parts"),
    dict(mode="air_standard", basis="per_kg", price_usd=Decimal("9.50"), min_charge_usd=Decimal("20.00"),
         transit_days_min=10, transit_days_max=15, sort_order=2,
         summary="Consolidated air cargo, a balance of speed and cost.",
         best_for="Clothing, cosmetics, small electronics, personal shopping"),
    dict(mode="sea", basis="per_cbm", price_usd=Decimal("280.00"), min_charge_usd=Decimal("140.00"),
         transit_days_min=45, transit_days_max=60, sort_order=3,
         summary="Shared container via Mombasa. Pay only for the space you use.",
         best_for="Business stock, furniture, bulky or heavy goods"),
    dict(mode="sea_fcl", basis="per_container", price_usd=Decimal("6500.00"), min_charge_usd=Decimal("0"),
         transit_days_min=40, transit_days_max=55, sort_order=4,
         summary="A full 40ft container dedicated to your goods.",
         best_for="Large importers, machinery, building materials"),
]


def seed(apps, schema_editor):
    ShippingRate = apps.get_model("data", "ShippingRate")
    for rate in RATES:
        ShippingRate.objects.update_or_create(mode=rate["mode"], defaults=rate)


def unseed(apps, schema_editor):
    apps.get_model("data", "ShippingRate").objects.filter(mode__in=[r["mode"] for r in RATES]).delete()


class Migration(migrations.Migration):
    dependencies = [("data", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
