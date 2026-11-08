from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "XpressDrive — Operations"
admin.site.site_title = "XpressDrive Admin"
admin.site.index_title = "Cargo operations"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/", include("apps.apis.urls")),
]
