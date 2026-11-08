"""All API routes, mounted at /api/ by config/urls.py."""
from django.urls import path

from apps.accounts import views as accounts
from apps.core import views as core
from apps.fleet import views as fleet
from apps.pricing import views as pricing
from apps.shipments import views as shipments
from apps.staff import views as staff

auth_urlpatterns = [
    path("auth/register/", accounts.RegisterView.as_view(), name="register"),
    path("auth/login/", accounts.LoginView.as_view(), name="login"),
    path("auth/refresh/", accounts.RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", accounts.LogoutView.as_view(), name="logout"),
    path("auth/me/", accounts.MeView.as_view(), name="me"),
    path("auth/password/change/", accounts.ChangePasswordView.as_view(), name="password-change"),
    path("auth/password/reset/", accounts.PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password/reset/confirm/", accounts.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]

shipment_urlpatterns = [
    path("shipments/", shipments.ShipmentListCreateView.as_view(), name="shipment-list"),
    path("shipments/summary/", shipments.DashboardSummaryView.as_view(), name="shipment-summary"),
    path("shipments/<str:tracking_number>/", shipments.ShipmentDetailView.as_view(), name="shipment-detail"),
    path("shipments/<str:tracking_number>/cancel/", shipments.ShipmentCancelView.as_view(), name="shipment-cancel"),
    path("track/<str:tracking_number>/", shipments.PublicTrackView.as_view(), name="public-track"),
]

pricing_urlpatterns = [
    path("rates/", pricing.ShippingRateListView.as_view(), name="rates"),
    path("rates/estimate/", pricing.EstimateView.as_view(), name="estimate"),
]

# Public lane data: towns/ports/borders, and return-truck space on offer.
fleet_public_urlpatterns = [
    path("places/", fleet.PlacesView.as_view(), name="places"),
    path("capacity/", fleet.CapacityView.as_view(), name="capacity"),
]

# Driver app: drivers only ever reach trips allocated to them.
driver_urlpatterns = [
    path("driver/summary/", fleet.DriverSummaryView.as_view(), name="driver-summary"),
    path("driver/trips/", fleet.DriverTripListView.as_view(), name="driver-trips"),
    path("driver/trips/<str:code>/", fleet.DriverTripDetailView.as_view(), name="driver-trip"),
    path("driver/trips/<str:code>/respond/", fleet.DriverTripRespondView.as_view(), name="driver-trip-respond"),
    path("driver/trips/<str:code>/status/", fleet.DriverTripStatusView.as_view(), name="driver-trip-status"),
    path("driver/trips/<str:code>/checkpoint/", fleet.DriverTripCheckpointView.as_view(), name="driver-trip-checkpoint"),
    path("driver/trips/<str:code>/positions/", fleet.DriverTripPositionsView.as_view(), name="driver-trip-positions"),
    path("driver/trips/<str:code>/bookings/<str:tracking_number>/delivered/", fleet.DriverDeliverView.as_view(), name="driver-deliver"),
    path("driver/empty-legs/", fleet.DriverEmptyLegListView.as_view(), name="driver-empty-legs"),
    path("driver/empty-legs/<int:pk>/", fleet.DriverEmptyLegDetailView.as_view(), name="driver-empty-leg"),
]

core_urlpatterns = [
    path("health/", core.HealthView.as_view(), name="health"),
    path("contact/", core.ContactCreateView.as_view(), name="contact"),
]

# Staff portal: active staff + Django model permissions (see apps/staff/permissions.py).
staff_urlpatterns = [
    path("staff/summary/", staff.StaffSummaryView.as_view(), name="staff-summary"),
    path("staff/shipments/", staff.StaffShipmentListView.as_view(), name="staff-shipments"),
    path("staff/shipments/bulk-status/", staff.StaffShipmentBulkStatusView.as_view(), name="staff-shipments-bulk-status"),
    path("staff/shipments/<str:tracking_number>/", staff.StaffShipmentDetailView.as_view(), name="staff-shipment"),
    path("staff/shipments/<str:tracking_number>/split/", staff.StaffShipmentSplitView.as_view(), name="staff-shipment-split"),
    path("staff/shipments/<str:tracking_number>/status/", staff.StaffShipmentStatusView.as_view(), name="staff-shipment-status"),
    path("staff/users/", staff.StaffUserListView.as_view(), name="staff-users"),
    path("staff/users/<str:customer_code>/", staff.StaffUserDetailView.as_view(), name="staff-user"),
    path("staff/users/<str:customer_code>/password-reset/", staff.StaffUserPasswordResetView.as_view(), name="staff-user-password-reset"),
    path("staff/rates/", staff.StaffRateListView.as_view(), name="staff-rates"),
    path("staff/rates/<slug:code>/", staff.StaffRateDetailView.as_view(), name="staff-rate"),
    path("staff/live/", staff.StaffLiveView.as_view(), name="staff-live"),
    path("staff/trips/", staff.StaffTripListView.as_view(), name="staff-trips"),
    path("staff/trips/<str:code>/", staff.StaffTripDetailView.as_view(), name="staff-trip"),
    path("staff/trips/<str:code>/allocate/", staff.StaffTripAllocateView.as_view(), name="staff-trip-allocate"),
    path("staff/trips/<str:code>/move/", staff.StaffTripMoveView.as_view(), name="staff-trip-move"),
    path("staff/trips/<str:code>/checkpoint/", staff.StaffTripCheckpointView.as_view(), name="staff-trip-checkpoint"),
    path("staff/trips/<str:code>/positions/", staff.StaffTripPositionsView.as_view(), name="staff-trip-positions"),
    path("staff/trucks/", staff.StaffTruckListView.as_view(), name="staff-trucks"),
    path("staff/trucks/<int:pk>/", staff.StaffTruckDetailView.as_view(), name="staff-truck"),
    path("staff/empty-legs/", staff.StaffEmptyLegListView.as_view(), name="staff-empty-legs"),
    path("staff/empty-legs/<int:pk>/", staff.StaffEmptyLegDetailView.as_view(), name="staff-empty-leg"),
    path("staff/empty-legs/<int:pk>/create-trip/", staff.StaffEmptyLegCreateTripView.as_view(), name="staff-empty-leg-trip"),
    path("staff/drivers/", staff.StaffDriverListView.as_view(), name="staff-drivers"),
    path("staff/messages/", staff.StaffMessageListView.as_view(), name="staff-messages"),
    path("staff/messages/<int:pk>/", staff.StaffMessageDetailView.as_view(), name="staff-message"),
]

urlpatterns = (
    auth_urlpatterns + shipment_urlpatterns + pricing_urlpatterns + fleet_public_urlpatterns + driver_urlpatterns
    + core_urlpatterns + staff_urlpatterns
)
