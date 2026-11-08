"""Staff portal API (/api/staff/...).

Every view requires an active staff account plus the Django model permission
for the section (see permissions.IsStaffWithModelPerm), the same grants the
Django admin uses. Customers get 403 everywhere.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.views import send_password_reset_email
from apps.data.models import (
    ACTIVE_STATUSES,
    CLOSED_STATUSES,
    TRIP_LIVE_STATUSES,
    ContactMessage,
    DriverResponse,
    EmptyLeg,
    EmptyLegStatus,
    PaymentStatus,
    Shipment,
    ShipmentStatus,
    ShippingRate,
    Trip,
    TripPosition,
    TripStatus,
    Truck,
)
from apps.fleet.serializers import (
    CheckpointSerializer,
    EmptyLegSerializer,
    PersonSerializer,
    TripEventSerializer,
    TripMoveSerializer,
    TripPositionSerializer,
    TripSerializer,
    TruckSerializer,
)
from .permissions import IsStaffWithModelPerm, staff_can
from .serializers import (
    AllocateSerializer,
    BulkStatusSerializer,
    StaffMessageSerializer,
    StaffRateSerializer,
    StaffShipmentDetailSerializer,
    StaffShipmentListSerializer,
    StaffShipmentUpdateSerializer,
    StaffUserSerializer,
    SplitSerializer,
    StatusChangeSerializer,
    TripFromEmptyLegSerializer,
)

User = get_user_model()


def _choice(params, name, allowed):
    value = params.get(name)
    if value and value not in allowed:
        raise ValidationError({name: "Unknown value."})
    return value


class StaffView:
    permission_classes = [IsStaffWithModelPerm]


# Dashboard groupings. The summary counts and the list's ?stage= filter both
# use these, so a dashboard number always matches the list it links to.
SHIPMENT_STAGES = {
    "booked": Q(status=ShipmentStatus.BOOKED),
    "awaiting_truck": Q(status=ShipmentStatus.CONFIRMED),
    "on_truck": Q(status__in=[ShipmentStatus.ALLOCATED, ShipmentStatus.LOADED]),
    "transit": Q(status__in=[ShipmentStatus.IN_TRANSIT, ShipmentStatus.AT_BORDER]),
    "arrived": Q(status=ShipmentStatus.ARRIVED),
    "on_hold": Q(status=ShipmentStatus.ON_HOLD),
    "no_trip": Q(trip__isnull=True, status__in=[ShipmentStatus.CONFIRMED, ShipmentStatus.ALLOCATED]),
    "awaiting_quote": Q(payment_status=PaymentStatus.PENDING) & ~Q(status__in=[ShipmentStatus.BOOKED, *CLOSED_STATUSES]),
    "unpaid": Q(payment_status=PaymentStatus.UNPAID),
}
# A live truck that has not reported its position for this long is flagged.
STALE_POSITION = timedelta(minutes=30)


# --------------------------------------------------------------------------- dashboard

class StaffSummaryView(StaffView, APIView):
    def get(self, request):
        data = {}
        if staff_can(request, "shipment"):
            qs = Shipment.objects.all()
            data["shipments"] = qs.aggregate(
                active=Count("id", filter=Q(status__in=ACTIVE_STATUSES)),
                booked=Count("id", filter=SHIPMENT_STAGES["booked"]),
                awaiting_truck=Count("id", filter=SHIPMENT_STAGES["awaiting_truck"]),
                on_truck=Count("id", filter=SHIPMENT_STAGES["on_truck"]),
                in_transit=Count("id", filter=SHIPMENT_STAGES["transit"]),
                arrived=Count("id", filter=SHIPMENT_STAGES["arrived"]),
                on_hold=Count("id", filter=SHIPMENT_STAGES["on_hold"]),
                no_trip=Count("id", filter=SHIPMENT_STAGES["no_trip"]),
                unpaid_count=Count("id", filter=SHIPMENT_STAGES["unpaid"]),
                unpaid_usd=Coalesce(Sum("charge_usd", filter=SHIPMENT_STAGES["unpaid"]), 0, output_field=Shipment._meta.get_field("charge_usd")),
                awaiting_quote=Count("id", filter=SHIPMENT_STAGES["awaiting_quote"]),
            )
            data["recent_shipments"] = StaffShipmentListSerializer(qs.select_related("owner", "trip")[:8], many=True).data
        if staff_can(request, "user"):
            data["customers"] = User.objects.filter(is_staff=False).aggregate(
                total=Count("id"), active=Count("id", filter=Q(is_active=True))
            )
        if staff_can(request, "trip"):
            stale_before = timezone.now() - STALE_POSITION
            data["trips"] = Trip.objects.aggregate(
                planned=Count("id", filter=Q(status=TripStatus.PLANNED)),
                awaiting_driver=Count("id", filter=Q(status=TripStatus.ALLOCATED)),
                live=Count("id", filter=Q(status__in=TRIP_LIVE_STATUSES)),
                declined=Count("id", filter=Q(status=TripStatus.PLANNED, driver_response=DriverResponse.DECLINED)),
                not_reporting=Count("id", filter=Q(status__in=[TripStatus.LOADING, TripStatus.IN_TRANSIT, TripStatus.AT_BORDER])
                                    & (Q(last_position_at__lt=stale_before) | Q(last_position_at__isnull=True))),
            )
        if staff_can(request, "emptyleg"):
            data["empty_legs_open"] = EmptyLeg.objects.filter(status=EmptyLegStatus.OPEN, available_from__gte=timezone.localdate() - timedelta(days=3)).count()
        if staff_can(request, "user"):
            data["drivers"] = User.objects.filter(is_driver=True, is_active=True).count()
        if staff_can(request, "contactmessage"):
            data["unhandled_messages"] = ContactMessage.objects.filter(handled=False).count()
        return Response(data)


# --------------------------------------------------------------------------- shipments

class StaffShipmentListView(StaffView, ListAPIView):
    staff_model = "shipment"
    serializer_class = StaffShipmentListSerializer

    def get_queryset(self):
        qs = Shipment.objects.select_related("owner", "trip")
        p = self.request.query_params
        state = p.get("state")
        if state == "active":
            qs = qs.filter(status__in=ACTIVE_STATUSES)
        elif state == "closed":
            qs = qs.filter(status__in=CLOSED_STATUSES)
        if s := _choice(p, "status", ShipmentStatus.values):
            qs = qs.filter(status=s)
        if stage := _choice(p, "stage", SHIPMENT_STAGES.keys()):
            qs = qs.filter(SHIPMENT_STAGES[stage])
        if m := p.get("mode"):
            qs = qs.filter(mode=m)
        if ps := _choice(p, "payment_status", PaymentStatus.values):
            qs = qs.filter(payment_status=ps)
        trip = p.get("trip")
        if trip == "none":
            qs = qs.filter(trip__isnull=True)
        elif trip:
            qs = qs.filter(trip__code=trip)
        for lane in ("origin", "destination"):
            if v := p.get(lane):
                qs = qs.filter(**{lane: v})
        if owner := p.get("owner"):
            qs = qs.filter(owner__customer_code=owner)
        q = (p.get("q") or "").strip()[:80]
        if q:
            qs = qs.filter(
                Q(tracking_number__icontains=q) | Q(consignee_name__icontains=q) | Q(description__icontains=q)
                | Q(owner__email__icontains=q) | Q(owner__customer_code__icontains=q) | Q(owner__phone__icontains=q)
                | Q(owner__first_name__icontains=q) | Q(owner__last_name__icontains=q)
            )
        ordering = p.get("ordering")
        if ordering in {"created_at", "-created_at", "updated_at", "-updated_at", "status", "-status"}:
            qs = qs.order_by(ordering)
        return qs


class StaffShipmentDetailView(StaffView, RetrieveUpdateAPIView):
    staff_model = "shipment"
    lookup_field = "tracking_number"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Shipment.objects.select_related("owner", "trip").prefetch_related("events__created_by")

    def get_serializer_class(self):
        return StaffShipmentUpdateSerializer if self.request.method == "PATCH" else StaffShipmentDetailSerializer

    def update(self, request, *args, **kwargs):
        shipment = self.get_object()
        serializer = self.get_serializer(shipment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StaffShipmentDetailSerializer(self.get_queryset().get(pk=shipment.pk)).data)


class StaffShipmentStatusView(StaffView, GenericAPIView):
    """Change status; always records a customer-visible tracking event."""

    staff_model = "shipment"
    lookup_field = "tracking_number"
    serializer_class = StatusChangeSerializer
    queryset = Shipment.objects.all()

    def post(self, request, tracking_number):
        shipment = self.get_object()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        shipment.update_status(d["status"], location=d["location"], note=d["note"], user=request.user)
        fresh = Shipment.objects.select_related("owner", "trip").prefetch_related("events__created_by").get(pk=shipment.pk)
        return Response(StaffShipmentDetailSerializer(fresh).data)


class StaffShipmentSplitView(StaffView, GenericAPIView):
    """Split a customer's cargo so part of it can travel on another truck.
    Creates a shipment, so needs add AND change permission on shipments."""

    staff_model = "shipment"
    staff_post_action = "add"
    lookup_field = "tracking_number"
    serializer_class = SplitSerializer
    queryset = Shipment.objects.all()

    def post(self, request, tracking_number):
        if not staff_can(request, "shipment", "change"):
            raise PermissionDenied("You also need permission to change bookings.")
        shipment = self.get_object()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            part = shipment.split(**s.validated_data, user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages}) from exc
        qs = Shipment.objects.select_related("owner", "trip", "parent").prefetch_related("events__created_by")
        return Response(
            {"original": StaffShipmentDetailSerializer(qs.get(pk=shipment.pk)).data, "part": StaffShipmentDetailSerializer(qs.get(pk=part.pk)).data},
            status=status.HTTP_201_CREATED,
        )


class StaffShipmentBulkStatusView(StaffView, GenericAPIView):
    staff_model = "shipment"
    serializer_class = BulkStatusSerializer

    @transaction.atomic
    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        updated = 0
        for shipment in Shipment.objects.select_for_update().filter(tracking_number__in=d["tracking_numbers"]):
            if shipment.status != d["status"]:
                shipment.update_status(d["status"], location=d["location"], note=d["note"], user=request.user)
                updated += 1
        return Response({"updated": updated})


# --------------------------------------------------------------------------- users

def _users_qs():
    return User.objects.annotate(
        shipment_count=Count("shipments", distinct=True),
        active_shipment_count=Count("shipments", filter=Q(shipments__status__in=ACTIVE_STATUSES), distinct=True),
    ).order_by("-date_joined")


class StaffUserListView(StaffView, ListAPIView):
    staff_model = "user"
    serializer_class = StaffUserSerializer

    def get_queryset(self):
        qs = _users_qs()
        p = self.request.query_params
        role = p.get("role")
        if role == "customers":
            qs = qs.filter(is_staff=False, is_driver=False)
        elif role == "staff":
            qs = qs.filter(is_staff=True)
        elif role == "drivers":
            qs = qs.filter(is_driver=True)
        active = p.get("active")
        if active in ("true", "false"):
            qs = qs.filter(is_active=active == "true")
        q = (p.get("q") or "").strip()[:80]
        if q:
            qs = qs.filter(
                Q(email__icontains=q) | Q(customer_code__icontains=q) | Q(phone__icontains=q)
                | Q(first_name__icontains=q) | Q(last_name__icontains=q)
            )
        return qs


class StaffUserDetailView(StaffView, RetrieveUpdateAPIView):
    staff_model = "user"
    serializer_class = StaffUserSerializer
    lookup_field = "customer_code"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return _users_qs()

    def perform_update(self, serializer):
        target = serializer.instance
        me = self.request.user
        if target.is_staff and not me.is_superuser and target.pk != me.pk:
            raise PermissionDenied("Only a superuser can edit other staff accounts.")
        if target.pk == me.pk and serializer.validated_data.get("is_active") is False:
            raise ValidationError({"is_active": "You cannot deactivate your own account."})
        serializer.save()


class StaffUserPasswordResetView(StaffView, GenericAPIView):
    """Email the user a password reset link. Staff never see or set passwords."""

    staff_model = "user"
    lookup_field = "customer_code"
    queryset = User.objects.all()

    def post(self, request, customer_code):
        user = self.get_object()
        if not user.is_active:
            raise ValidationError({"detail": "This account is deactivated. Reactivate it first."})
        if user.is_staff and not request.user.is_superuser and user.pk != request.user.pk:
            raise PermissionDenied("Only a superuser can reset other staff accounts.")
        send_password_reset_email(user)
        return Response({"detail": f"Password reset link sent to {user.email}."})


# --------------------------------------------------------------------------- rates

class StaffRateListView(StaffView, ListCreateAPIView):
    """List all pricing plans, or add one (needs the add permission + scope)."""

    staff_model = "shippingrate"
    staff_post_action = "add"
    serializer_class = StaffRateSerializer
    pagination_class = None
    queryset = ShippingRate.objects.all()


class StaffRateDetailView(StaffView, RetrieveUpdateDestroyAPIView):
    """Edit or delete a plan. Deleting needs the delete permission + scope;
    shipments are unaffected (they record mode and charges, not the plan)."""

    staff_model = "shippingrate"
    serializer_class = StaffRateSerializer
    lookup_field = "code"
    queryset = ShippingRate.objects.all()
    http_method_names = ["get", "patch", "delete", "head", "options"]


# --------------------------------------------------------------------------- trips

def _trips_qs():
    return Trip.objects.select_related("driver", "truck", "empty_leg").annotate(
        shipment_count=Count("shipments", filter=~Q(shipments__status=ShipmentStatus.CANCELLED), distinct=True),
        used_cbm=Coalesce(Sum("shipments__volume_cbm"), 0, output_field=Trip._meta.get_field("capacity_cbm")),
        used_kg=Coalesce(Sum("shipments__weight_kg"), 0, output_field=Trip._meta.get_field("capacity_kg")),
    )


class StaffTripListView(StaffView, ListCreateAPIView):
    staff_model = "trip"
    staff_post_action = "add"
    serializer_class = TripSerializer

    def get_queryset(self):
        qs = _trips_qs()
        p = self.request.query_params
        if s := _choice(p, "status", TripStatus.values):
            qs = qs.filter(status=s)
        state = p.get("state")
        if state == "open":
            qs = qs.filter(status__in=[TripStatus.PLANNED, TripStatus.ALLOCATED, TripStatus.ACCEPTED, TripStatus.LOADING])
        elif state == "live":
            qs = qs.filter(status__in=TRIP_LIVE_STATUSES)
        elif state == "closed":
            qs = qs.filter(status__in=[TripStatus.COMPLETED, TripStatus.CANCELLED])
        if p.get("backhaul") == "true":
            qs = qs.filter(is_backhaul=True)
        for lane in ("origin", "destination"):
            if v := p.get(lane):
                qs = qs.filter(**{lane: v})
        if driver := p.get("driver"):
            qs = qs.filter(driver__customer_code=driver)
        q = (p.get("q") or "").strip()[:80]
        if q:
            qs = qs.filter(
                Q(code__icontains=q) | Q(carrier_reference__icontains=q) | Q(truck__plate_number__icontains=q)
                | Q(driver__first_name__icontains=q) | Q(driver__last_name__icontains=q) | Q(driver__phone__icontains=q)
            )
        return qs

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        trip = s.save()
        trip.log("note", status=trip.status, note="Trip created.", user=request.user)
        return Response(TripSerializer(_trips_qs().get(pk=trip.pk)).data, status=status.HTTP_201_CREATED)


class StaffTripDetailView(StaffView, RetrieveUpdateAPIView):
    staff_model = "trip"
    serializer_class = TripSerializer
    lookup_field = "code"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return _trips_qs()

    def retrieve(self, request, *args, **kwargs):
        trip = self.get_object()
        shipments = trip.shipments.select_related("owner", "trip")
        return Response({
            **TripSerializer(trip).data,
            "shipments": StaffShipmentListSerializer(shipments, many=True).data,
            "events": TripEventSerializer(trip.events.select_related("created_by")[:100], many=True).data,
        })

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return self.retrieve(request, *args, **kwargs)


class StaffTripAllocateView(StaffView, GenericAPIView):
    """Offer the trip to a driver; it appears in their app to accept or decline."""

    staff_model = "trip"
    serializer_class = AllocateSerializer
    lookup_field = "code"
    queryset = Trip.objects.all()

    def post(self, request, code):
        trip = self.get_object()
        if trip.status not in (TripStatus.PLANNED, TripStatus.ALLOCATED, TripStatus.ACCEPTED):
            raise ValidationError({"detail": "This trip is already under way; it cannot be reallocated."})
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        truck = None
        if d.get("truck_id"):
            truck = Truck.objects.filter(pk=d["truck_id"], is_active=True).first()
            if truck is None:
                raise ValidationError({"truck_id": "Unknown or inactive truck."})
        driver = d["driver"]
        busy = Trip.objects.filter(driver=driver, status__in=[TripStatus.LOADING, TripStatus.IN_TRANSIT, TripStatus.AT_BORDER]).exclude(pk=trip.pk).first()
        if busy:
            raise ValidationError({"driver": f"{driver.get_full_name()} is on trip {busy.code} right now."})
        trip.allocate(driver, truck, user=request.user, note=d["note"])
        return Response(TripSerializer(_trips_qs().get(pk=trip.pk)).data)


class StaffTripMoveView(StaffView, GenericAPIView):
    """Move a trip (and every open booking on it) to a stage. Staff may set any
    stage, e.g. on behalf of a driver without signal, or to cancel."""

    staff_model = "trip"
    serializer_class = TripMoveSerializer
    lookup_field = "code"
    queryset = Trip.objects.all()

    @transaction.atomic
    def post(self, request, code):
        if not staff_can(request, "shipment", "change"):
            raise PermissionDenied("You also need permission to change bookings.")
        trip = self.get_object()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        moved = trip.advance(d["status"], place=d["place"], place_label=d["place_label"], note=d["note"], user=request.user)
        if d["status"] == TripStatus.CANCELLED:
            # Open cargo goes back to the "needs a truck" queue.
            moved = trip.shipments.exclude(status__in=CLOSED_STATUSES).update(trip=None)
            if hasattr(trip, "empty_leg") and trip.empty_leg:
                EmptyLeg.objects.filter(pk=trip.empty_leg.pk).update(status=EmptyLegStatus.OPEN, trip=None)
        return Response({"moved": moved, "trip": TripSerializer(_trips_qs().get(pk=trip.pk)).data})


class StaffTripCheckpointView(StaffView, GenericAPIView):
    staff_model = "trip"
    serializer_class = CheckpointSerializer
    lookup_field = "code"
    queryset = Trip.objects.all()

    def post(self, request, code):
        trip = self.get_object()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        n = trip.checkpoint(place=d["place"], place_label=d["place_label"], note=d["note"], user=request.user)
        return Response({"updated": n})


class StaffTripPositionsView(StaffView, GenericAPIView):
    """GPS trail of one trip (oldest first), for the trip map."""

    staff_model = "trip"
    lookup_field = "code"
    queryset = Trip.objects.all()
    MAX_POINTS = 2000

    def get(self, request, code):
        trip = self.get_object()
        qs = TripPosition.objects.filter(trip=trip)
        since = request.query_params.get("since")
        if since:
            from django.utils.dateparse import parse_datetime

            dt = parse_datetime(since)
            if dt is None:
                raise ValidationError({"since": "Use an ISO date-time."})
            qs = qs.filter(recorded_at__gt=dt)
        total = qs.count()
        points = list(qs.order_by("recorded_at"))
        if total > self.MAX_POINTS:  # thin evenly, always keep the latest fix
            step = total / self.MAX_POINTS
            points = [points[int(i * step)] for i in range(self.MAX_POINTS - 1)] + [points[-1]]
        return Response({"count": total, "positions": TripPositionSerializer(points, many=True).data})


class StaffLiveView(StaffView, APIView):
    """Trips under way with their last known position, for the live dashboard map."""

    staff_model = "trip"

    def get(self, request):
        stale_before = timezone.now() - STALE_POSITION
        trips = _trips_qs().filter(status__in=[TripStatus.ALLOCATED, *TRIP_LIVE_STATUSES]).order_by("-last_position_at")
        rows = []
        for t in trips:
            row = TripSerializer(t).data
            row["stale"] = t.status != TripStatus.ALLOCATED and (t.last_position_at is None or t.last_position_at < stale_before)
            rows.append(row)
        return Response({"trips": rows, "server_time": timezone.now()})


# --------------------------------------------------------------------------- trucks

class StaffTruckListView(StaffView, ListCreateAPIView):
    staff_model = "truck"
    staff_post_action = "add"
    serializer_class = TruckSerializer

    def get_queryset(self):
        qs = Truck.objects.select_related("default_driver")
        p = self.request.query_params
        if p.get("active") in ("true", "false"):
            qs = qs.filter(is_active=p["active"] == "true")
        if t := p.get("type"):
            qs = qs.filter(truck_type=t)
        q = (p.get("q") or "").strip()[:40]
        if q:
            qs = qs.filter(Q(plate_number__icontains=q) | Q(trailer_plate__icontains=q) | Q(owner_name__icontains=q))
        return qs


class StaffTruckDetailView(StaffView, RetrieveUpdateAPIView):
    staff_model = "truck"
    serializer_class = TruckSerializer
    queryset = Truck.objects.select_related("default_driver")
    http_method_names = ["get", "patch", "head", "options"]


# --------------------------------------------------------------------------- empty legs

class StaffEmptyLegListView(StaffView, ListAPIView):
    staff_model = "emptyleg"
    serializer_class = EmptyLegSerializer

    def get_queryset(self):
        qs = EmptyLeg.objects.select_related("driver", "truck", "trip")
        p = self.request.query_params
        if s := _choice(p, "status", EmptyLegStatus.values):
            qs = qs.filter(status=s)
        if p.get("current") == "true":
            qs = qs.filter(available_from__gte=timezone.localdate() - timedelta(days=3))
        for lane in ("origin", "destination"):
            if v := p.get(lane):
                qs = qs.filter(**{lane: v})
        return qs


class StaffEmptyLegDetailView(StaffView, RetrieveUpdateAPIView):
    staff_model = "emptyleg"
    serializer_class = EmptyLegSerializer
    queryset = EmptyLeg.objects.select_related("driver", "truck", "trip")
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        new = self.request.data.get("status") if hasattr(self.request.data, "get") else None
        if new:
            if new not in (EmptyLegStatus.OPEN, EmptyLegStatus.EXPIRED, EmptyLegStatus.WITHDRAWN):
                raise ValidationError({"status": "Use 'Create trip' to match an offer."})
            serializer.save(status=new)
        else:
            serializer.save()


class StaffEmptyLegCreateTripView(StaffView, GenericAPIView):
    """Turn a driver's empty-leg offer into a backhaul trip (optionally allocated
    to that driver straight away), ready to be filled with bookings."""

    staff_model = "trip"
    staff_post_action = "add"
    serializer_class = TripFromEmptyLegSerializer
    queryset = EmptyLeg.objects.select_related("driver", "truck")

    @transaction.atomic
    def post(self, request, pk):
        if not staff_can(request, "emptyleg", "change"):
            raise PermissionDenied("You also need permission to change empty legs.")
        leg = get_object_or_404(EmptyLeg.objects.select_for_update(of=("self",)).select_related("driver", "truck"), pk=pk)
        if leg.status != EmptyLegStatus.OPEN:
            raise ValidationError({"detail": "This offer is no longer open."})
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        trip = Trip.objects.create(
            origin=leg.origin, destination=leg.destination, is_backhaul=True, truck=leg.truck,
            capacity_kg=leg.capacity_kg or (leg.truck.capacity_kg if leg.truck_id else None),
            capacity_cbm=leg.capacity_cbm or (leg.truck.capacity_cbm if leg.truck_id else None),
            departure_date=d.get("departure_date") or leg.available_from, eta_date=d.get("eta_date"),
            notes=f"From empty-leg offer: {leg.get_space_display()}. {leg.notes}".strip(),
        )
        trip.log("note", status=trip.status, note="Created from a driver's empty-leg offer.", user=request.user)
        leg.status = EmptyLegStatus.MATCHED
        leg.trip = trip
        leg.save(update_fields=["status", "trip", "updated_at"])
        if d["allocate"] and leg.driver.is_active and leg.driver.is_driver:
            trip.allocate(leg.driver, leg.truck, user=request.user, note="Allocated to the driver who offered this empty leg.")
        return Response(TripSerializer(_trips_qs().get(pk=trip.pk)).data, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------- drivers

class StaffDriverListView(StaffView, APIView):
    """Drivers with their current trip and last report, for allocation pickers."""

    staff_model = "user"

    def get(self, request):
        drivers = User.objects.filter(is_driver=True)
        if request.query_params.get("active") != "all":
            drivers = drivers.filter(is_active=True)
        current = {
            t.driver_id: t for t in Trip.objects.filter(
                driver__in=drivers, status__in=[TripStatus.ALLOCATED, *TRIP_LIVE_STATUSES]
            ).order_by("allocated_at")
        }
        rows = []
        for d in drivers.order_by("first_name", "last_name"):
            t = current.get(d.pk)
            rows.append({
                **PersonSerializer(d).data,
                "email": d.email, "licence_number": d.licence_number, "is_active": d.is_active,
                "trucks": [{"id": tr.id, "plate_number": tr.plate_number} for tr in d.trucks.filter(is_active=True)],
                "current_trip": {"code": t.code, "status": t.status, "status_display": t.get_status_display(),
                                 "last_position_at": t.last_position_at} if t else None,
            })
        return Response(rows)


# --------------------------------------------------------------------------- contact messages

class StaffMessageListView(StaffView, ListAPIView):
    staff_model = "contactmessage"
    serializer_class = StaffMessageSerializer

    def get_queryset(self):
        qs = ContactMessage.objects.all()
        handled = self.request.query_params.get("handled")
        if handled in ("true", "false"):
            qs = qs.filter(handled=handled == "true")
        return qs


class StaffMessageDetailView(StaffView, RetrieveUpdateAPIView):
    staff_model = "contactmessage"
    serializer_class = StaffMessageSerializer
    queryset = ContactMessage.objects.all()
    http_method_names = ["get", "patch", "head", "options"]
