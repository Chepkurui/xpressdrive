from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.data.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "customer_code", "first_name", "last_name", "phone", "is_active", "is_driver", "is_staff", "date_joined"]
    list_filter = ["is_active", "is_driver", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name", "phone", "customer_code"]
    readonly_fields = ["customer_code", "last_login", "date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password", "customer_code")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        ("Driver", {"fields": ("is_driver", "licence_number")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "phone", "password1", "password2")}),
    )
