from django.contrib import admin

from apps.data.models import ShippingRate


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "mode", "origin", "destination", "basis", "price_usd", "min_charge_usd", "transit_days_min", "transit_days_max", "is_active", "sort_order"]
    list_filter = ["mode", "origin", "destination", "is_active"]
    prepopulated_fields = {"code": ("name",)}
    readonly_fields = ["basis"]
    list_editable = ["price_usd", "min_charge_usd", "transit_days_min", "transit_days_max", "is_active", "sort_order"]
