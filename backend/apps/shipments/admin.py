from django.contrib import admin, messages

from apps.data.models import (
    EmptyLeg,
    Shipment,
    ShipmentStatus,
    TrackingEvent,
    Trip,
    TripEvent,
    TripPosition,
    TripStatus,
    Truck,
)


def make_shipment_status_action(status):
    def action(modeladmin, request, queryset):
        count = 0
        for shipment in queryset:
            if shipment.status != status:
                shipment.update_status(status, user=request.user)
                count += 1
        modeladmin.message_user(request, f"{count} booking(s) set to '{status.label}'.", messages.SUCCESS)

    action.__name__ = f"mark_{status.value}"
    action.short_description = f"Mark selected as: {status.label}"
    return action


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    extra = 0
    fields = ["created_at", "status", "location", "note", "created_by"]
    readonly_fields = ["created_by"]
    ordering = ["-created_at"]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "tracking_number", "owner", "description", "origin", "destination", "mode", "status",
        "trip", "weight_kg", "charge_usd", "payment_status", "created_at",
    ]
    list_filter = ["status", "mode", "origin", "destination", "service_type", "payment_status", "category"]
    search_fields = ["tracking_number", "description", "consignee_name", "owner__email", "owner__customer_code", "owner__phone"]
    autocomplete_fields = ["owner", "trip"]
    readonly_fields = ["tracking_number", "created_at", "updated_at", "received_at", "delivered_at"]
    list_select_related = ["owner", "trip"]
    inlines = [TrackingEventInline]
    actions = [make_shipment_status_action(s) for s in ShipmentStatus]
    fieldsets = (
        ("Identity", {"fields": ("tracking_number", "owner", "trip", "status")}),
        ("Route", {"fields": ("origin", "destination", "pickup_address", "pickup_date")}),
        ("Customer declaration", {"fields": (
            "description", "category", "mode", "service_type", "quantity", "declared_weight_kg",
            "declared_value_usd", "is_hazardous", "is_fragile", "consignee_name", "consignee_phone",
            "delivery_option", "delivery_address", "customer_notes",
        )}),
        ("Measurements & billing", {"fields": ("weight_kg", "volume_cbm", "packages_received", "charge_usd", "payment_status", "eta_date", "internal_notes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "received_at", "delivered_at")}),
    )

    def save_model(self, request, obj, form, change):
        status_changed = change and "status" in form.changed_data
        new_status = obj.status
        if status_changed:
            # Record the change through update_status so a timeline event is created.
            obj.status = form.initial.get("status")
        super().save_model(request, obj, form, change)
        if status_changed:
            obj.update_status(new_status, user=request.user)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for inst in instances:
            if isinstance(inst, TrackingEvent) and not inst.created_by_id:
                inst.created_by = request.user
            inst.save()
        for obj in formset.deleted_objects:
            obj.delete()


class ShipmentInline(admin.TabularInline):
    model = Shipment
    fields = ["tracking_number", "owner", "description", "status", "weight_kg", "volume_cbm"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True


class TripEventInline(admin.TabularInline):
    model = TripEvent
    fields = ["created_at", "kind", "status", "place_label", "note", "lat", "lng", "created_by"]
    readonly_fields = fields
    extra = 0
    can_delete = False


def make_trip_status_action(status):
    def action(modeladmin, request, queryset):
        moved = sum(trip.advance(status, user=request.user) for trip in queryset)
        modeladmin.message_user(request, f"Trip(s) moved; {moved} booking(s) updated.", messages.SUCCESS)

    action.__name__ = f"trip_{status.value}"
    action.short_description = f"Move trip to: {status.label}"
    return action


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["code", "origin", "destination", "is_backhaul", "status", "driver", "truck", "departure_date", "eta_date", "fill", "booking_count"]
    list_filter = ["status", "is_backhaul", "origin", "destination"]
    search_fields = ["code", "carrier_reference", "truck__plate_number", "driver__email", "driver__first_name", "driver__last_name"]
    autocomplete_fields = ["driver", "truck"]
    readonly_fields = ["allocated_at", "responded_at", "started_at", "completed_at", "last_lat", "last_lng", "last_speed_kmh", "last_heading", "last_position_at"]
    inlines = [ShipmentInline, TripEventInline]
    actions = [make_trip_status_action(s) for s in (TripStatus.LOADING, TripStatus.IN_TRANSIT, TripStatus.AT_BORDER, TripStatus.ARRIVED, TripStatus.COMPLETED)]

    @admin.display(description="Bookings")
    def booking_count(self, obj):
        return obj.shipments.count()

    @admin.display(description="Fill")
    def fill(self, obj):
        if obj.capacity_cbm:
            return f"{obj.used_cbm()} / {obj.capacity_cbm} CBM"
        if obj.capacity_kg:
            return f"{obj.used_kg()} / {obj.capacity_kg} kg"
        return "—"


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "trailer_plate", "truck_type", "capacity_kg", "capacity_cbm", "home_base", "default_driver", "owner_name", "is_active"]
    list_filter = ["truck_type", "home_base", "is_active"]
    search_fields = ["plate_number", "trailer_plate", "owner_name"]
    autocomplete_fields = ["default_driver"]


@admin.register(EmptyLeg)
class EmptyLegAdmin(admin.ModelAdmin):
    list_display = ["origin", "destination", "available_from", "space", "driver", "truck", "status", "trip"]
    list_filter = ["status", "space", "origin", "destination"]
    search_fields = ["driver__email", "driver__first_name", "driver__last_name", "truck__plate_number"]
    autocomplete_fields = ["driver", "truck", "trip"]


@admin.register(TripPosition)
class TripPositionAdmin(admin.ModelAdmin):
    list_display = ["trip", "recorded_at", "lat", "lng", "speed_kmh", "accuracy_m"]
    list_filter = ["trip__status"]
    search_fields = ["trip__code"]
    readonly_fields = [f.name for f in TripPosition._meta.fields]

    def has_add_permission(self, request):
        return False
