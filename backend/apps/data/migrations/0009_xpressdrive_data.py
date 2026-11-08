"""Convert China-route data to XpressDrive road freight.

- booking statuses, load types and categories mapped to road equivalents
- trip (ex-batch) statuses mapped
- *_batch permissions renamed to *_trip; staff roles get fleet permissions
- the air/sea rate card is replaced with indicative road-freight plans
"""
from decimal import Decimal

from django.contrib.auth.management import create_permissions
from django.db import migrations

SHIPMENT_STATUS = {
    "pre_alert": "booked", "received": "confirmed", "consolidating": "confirmed", "departed": "in_transit",
    "arrived_hub": "in_transit", "customs": "at_border", "in_transit_ug": "in_transit", "ready": "arrived",
}
MODE = {"air_express": "parcel", "air_standard": "parcel", "sea": "part_load", "sea_fcl": "container_40"}
CATEGORY = {"cosmetics": "fmcg"}
TRIP_STATUS = {"open": "planned", "closed": "loading", "departed": "in_transit", "arrived": "arrived", "completed": "completed"}

RATES = [
    dict(code="parcel", name="Parcel", mode="parcel", basis="per_kg", price_usd=Decimal("0.90"), min_charge_usd=Decimal("10.00"),
         transit_days_min=1, transit_days_max=4, sort_order=1,
         summary="Small consignments on our scheduled trucks across the region.",
         best_for="Boxes, spare parts, documents, shop restocks"),
    dict(code="part-load", name="Part load (shared truck)", mode="part_load", basis="per_cbm", price_usd=Decimal("38.00"),
         min_charge_usd=Decimal("60.00"), transit_days_min=2, transit_days_max=6, sort_order=2,
         summary="Share a truck with other cargo going the same way. Pay only for the space you use.",
         best_for="Pallets, business stock, furniture"),
    dict(code="full-truck", name="Full truck load", mode="full_truck", basis="per_container", price_usd=Decimal("1500.00"),
         min_charge_usd=Decimal("0"), transit_days_min=2, transit_days_max=5, sort_order=3,
         summary="A whole truck (up to 30 t) dedicated to your cargo, door to door.",
         best_for="Bulk goods, produce, building materials"),
    dict(code="container-20", name="20ft container", mode="container_20", basis="per_container", price_usd=Decimal("1900.00"),
         min_charge_usd=Decimal("0"), transit_days_min=3, transit_days_max=7, sort_order=4,
         summary="Container haulage from the port or ICD to your door.",
         best_for="Importers clearing at Mombasa or Dar es Salaam"),
    dict(code="container-40", name="40ft container", mode="container_40", basis="per_container", price_usd=Decimal("2600.00"),
         min_charge_usd=Decimal("0"), transit_days_min=3, transit_days_max=7, sort_order=5,
         summary="40ft container haulage anywhere in the region, including DR Congo and South Sudan.",
         best_for="Large importers, machinery, transit cargo"),
    dict(code="backhaul-40", name="Return-leg 40ft (backhaul)", mode="container_40", basis="per_container",
         price_usd=Decimal("1700.00"), min_charge_usd=Decimal("0"), transit_days_min=3, transit_days_max=8, sort_order=6,
         summary="Fill a container that is heading back to base anyway, at a lower price. Dates follow the truck.",
         best_for="Flexible cargo going to Mombasa, Nairobi or Kampala"),
]

ROLE_PERMS = {
    "Operations": ["view_trip", "add_trip", "change_trip", "view_truck", "add_truck", "change_truck",
                   "view_emptyleg", "change_emptyleg", "change_user"],
    "Customer support": ["view_trip", "view_emptyleg"],
}


def forwards(apps, schema_editor):
    Shipment = apps.get_model("data", "Shipment")
    TrackingEvent = apps.get_model("data", "TrackingEvent")
    Trip = apps.get_model("data", "Trip")
    ShippingRate = apps.get_model("data", "ShippingRate")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Group = apps.get_model("auth", "Group")

    for old, new in SHIPMENT_STATUS.items():
        Shipment.objects.filter(status=old).update(status=new)
        TrackingEvent.objects.filter(status=old).update(status=new)
    for old, new in MODE.items():
        Shipment.objects.filter(mode=old).update(mode=new)
    for old, new in CATEGORY.items():
        Shipment.objects.filter(category=old).update(category=new)
    for old, new in TRIP_STATUS.items():
        Trip.objects.filter(status=old).update(status=new)
    TrackingEvent.objects.filter(location__in=["Guangzhou, China", "China"]).update(location="")

    ShippingRate.objects.filter(mode__in=list(MODE)).delete()
    for rate in RATES:
        ShippingRate.objects.update_or_create(code=rate["code"], defaults=rate)

    # Batch was renamed Trip: keep existing role grants by renaming the permissions.
    trip_ct, _ = ContentType.objects.get_or_create(app_label="data", model="trip")
    for perm in Permission.objects.filter(content_type__app_label="data", codename__endswith="_batch"):
        codename = perm.codename.replace("_batch", "_trip")
        if Permission.objects.filter(content_type=trip_ct, codename=codename).exists():
            perm.delete()
            continue
        perm.codename = codename
        perm.name = f"Can {codename.split('_')[0]} trip"
        perm.content_type = trip_ct
        perm.save()
    ContentType.objects.filter(app_label="data", model="batch").delete()

    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None
    for name, codenames in ROLE_PERMS.items():
        group = Group.objects.filter(name=name).first()
        if group:
            group.permissions.add(*Permission.objects.filter(content_type__app_label="data", codename__in=codenames))


class Migration(migrations.Migration):
    dependencies = [("data", "0008_xpressdrive_fleet"), ("contenttypes", "0002_remove_content_type_name"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
