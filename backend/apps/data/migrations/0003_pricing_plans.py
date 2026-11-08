"""Turn the one-rate-per-mode card into pricing plans (several plans per mode).
Existing rates keep their mode as their code, so old URLs and clients still work."""
from django.db import migrations, models

NAMES = {
    "air_express": "Air Express",
    "air_standard": "Air Standard",
    "sea": "Sea Freight (LCL consolidation)",
    "sea_fcl": "Sea Freight (Full container)",
}


def fill_codes(apps, schema_editor):
    ShippingRate = apps.get_model("data", "ShippingRate")
    for rate in ShippingRate.objects.all():
        rate.code = rate.mode
        rate.name = NAMES.get(rate.mode, rate.mode)
        rate.save(update_fields=["code", "name"])


class Migration(migrations.Migration):
    dependencies = [("data", "0002_seed_rates")]

    operations = [
        # db_index=False: on Postgres, SlugField's default index plus the later
        # unique=True would both create "..._code_..._like" and collide.
        migrations.AddField("shippingrate", "code", models.SlugField(max_length=40, null=True, db_index=False)),
        migrations.AddField("shippingrate", "name", models.CharField(max_length=80, default="")),
        migrations.AddField("shippingrate", "created_at", models.DateTimeField(auto_now_add=True, null=True)),
        migrations.RunPython(fill_codes, migrations.RunPython.noop),
        migrations.AlterField(
            "shippingrate", "code",
            models.SlugField(max_length=40, unique=True, help_text="Short, permanent identifier used in URLs and the API."),
        ),
        migrations.AlterField("shippingrate", "name", models.CharField(max_length=80)),
        migrations.AlterField(
            "shippingrate", "mode",
            models.CharField(max_length=20, choices=[("air_express", "Air Express"), ("air_standard", "Air Standard"), ("sea", "Sea Freight (LCL consolidation)"), ("sea_fcl", "Sea Freight (Full container)")]),
        ),
        migrations.AlterModelOptions("shippingrate", {"ordering": ["sort_order", "name"], "verbose_name": "pricing plan"}),
    ]
