from django.contrib import admin

from apps.data.models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["subject", "name", "email", "phone", "created_at", "handled"]
    list_filter = ["handled", "created_at"]
    search_fields = ["name", "email", "subject", "message"]
    list_editable = ["handled"]
    readonly_fields = ["name", "email", "phone", "subject", "message", "created_at"]
