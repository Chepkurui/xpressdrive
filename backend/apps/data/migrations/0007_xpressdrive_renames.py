"""XpressDrive: China-batch model becomes a road Trip; bookings gain a route.

Renames (not drop/add) so existing rows survive. Remaining field changes are in
0008 and the data conversion (statuses, load types, rate card, roles) in 0009.
"""
from django.db import migrations, models


def clear_china_fields(apps, schema_editor):
    # supplier name / China courier number mean nothing for road bookings, and
    # consignee_phone is shortened to 30 characters in 0008.
    apps.get_model("data", "Shipment").objects.update(consignee_name="", consignee_phone="")


class Migration(migrations.Migration):
    dependencies = [("data", "0006_parcel_shipment_labels")]

    operations = [
        migrations.RenameModel("Batch", "Trip"),
        migrations.RenameField("shipment", "batch", "trip"),
        migrations.RemoveField("trip", "mode"),
        migrations.RenameField("shipment", "supplier_name", "consignee_name"),
        migrations.RenameField("shipment", "supplier_tracking_number", "consignee_phone"),
        migrations.RenameField("shipment", "contains_battery", "is_hazardous"),
        migrations.RunPython(clear_china_fields, migrations.RunPython.noop),
        migrations.AddField("trip", "origin", models.CharField(default="mombasa", max_length=30), preserve_default=False),
        migrations.AddField("trip", "destination", models.CharField(default="kampala", max_length=30), preserve_default=False),
        migrations.AddField("shipment", "origin", models.CharField(default="mombasa", max_length=30), preserve_default=False),
        migrations.AddField("shipment", "destination", models.CharField(default="kampala", max_length=30), preserve_default=False),
    ]
