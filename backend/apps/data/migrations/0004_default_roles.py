"""Default staff roles (Django groups). Assign them to staff in the admin; a
user's sign-in tokens are scoped to what their roles allow."""
from django.contrib.auth.management import create_permissions
from django.db import migrations

ROLES = {
    "Operations": [
        "view_shipment", "add_shipment", "change_shipment",
        "view_batch", "add_batch", "change_batch",
        "view_user", "view_shippingrate", "view_contactmessage",
    ],
    "Pricing manager": ["view_shippingrate", "add_shippingrate", "change_shippingrate", "delete_shippingrate"],
    "Customer support": [
        "view_shipment", "view_batch", "view_user", "change_user",
        "view_shippingrate", "view_contactmessage", "change_contactmessage",
    ],
}


def create_roles(apps, schema_editor):
    # Permissions are normally created after migrate; make sure they exist now.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for name, codenames in ROLES.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.add(*Permission.objects.filter(content_type__app_label="data", codename__in=codenames))


def remove_roles(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [("data", "0003_pricing_plans"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(create_roles, remove_roles)]
