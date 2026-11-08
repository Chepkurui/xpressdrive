"""Driver app API (/api/driver/...) and public lane/capacity endpoints.

A driver only ever sees trips allocated to them: every query is filtered by
driver=request.user, so anyone else's trip is a 404.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDriver
from apps.data.models import (
    CLOSED_STATUSES,
    DRIVER_NEXT_STATUS,
    TRIP_LIVE_STATUSES,
    DriverResponse,
    EmptyLeg,
    EmptyLegStatus,
    ShipmentStatus,
    SpaceType,
    Trip,
    TripPosition,
    TripStatus,
    Truck,
    place_name,
    places_payload,
)
from .serializers import (
    CheckpointSerializer,
    DriverTripDetailSerializer,
    DriverTripSerializer,
    EmptyLegSerializer,
    PositionBatchSerializer,
    PublicCapacitySerializer,
    RespondSerializer,
    TripMoveSerializer,
    TruckBriefSerializer,
)

TRIP_SPACE = {
    "container_20": SpaceType.EMPTY_CONTAINER_20,
    "container_40": SpaceType.EMPTY_CONTAINER_40,
}


# --------------------------------------------------------------------------- public

class PlacesView(APIView):
    """Towns, ports and border posts served (for route pickers)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(places_payload())


class CapacityView(APIView):
    """Return-truck space on offer: open empty legs and planned backhaul trips.
    Lane, dates and space type only — never driver, truck or plate."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "capacity"

    def get(self, request):
        today = timezone.localdate()
        rows = []
        legs = EmptyLeg.objects.filter(status=EmptyLegStatus.OPEN).filter(
            Q(available_until__gte=today) | Q(available_until__isnull=True, available_from__gte=today)
        )
        for leg in legs[:50]:
            rows.append({
                "origin": leg.origin, "origin_name": place_name(leg.origin),
                "destination": leg.destination, "destination_name": place_name(leg.destination),
                "date_from": leg.available_from, "date_to": leg.available_until,
                "space": leg.space, "space_display": leg.get_space_display(),
            })
        trips = Trip.objects.filter(
            is_backhaul=True, status__in=[TripStatus.PLANNED, TripStatus.ALLOCATED, TripStatus.ACCEPTED],
        ).filter(Q(departure_date__gte=today) | Q(departure_date__isnull=True)).select_related("truck")
        for trip in trips[:50]:
            space = TRIP_SPACE.get(trip.truck.truck_type if trip.truck_id else "", SpaceType.PARTIAL)
            rows.append({
                "origin": trip.origin, "origin_name": trip.origin_name,
                "destination": trip.destination, "destination_name": trip.destination_name,
                "date_from": trip.departure_date, "date_to": trip.eta_date,
                "space": space, "space_display": SpaceType(space).label,
            })
        rows.sort(key=lambda r: (r["date_from"] is None, r["date_from"] or today))
        return Response(PublicCapacitySerializer(rows, many=True).data)


# --------------------------------------------------------------------------- driver

class DriverView:
    permission_classes = [IsDriver]


def _my_trips(request):
    return Trip.objects.filter(driver=request.user).select_related("truck").annotate(
        shipment_count=Count("shipments", filter=~Q(shipments__status=ShipmentStatus.CANCELLED))
    )


class DriverSummaryView(DriverView, APIView):
    def get(self, request):
        trips = _my_trips(request)
        pending = trips.filter(status=TripStatus.ALLOCATED, driver_response=DriverResponse.PENDING)
        active = trips.filter(status__in=TRIP_LIVE_STATUSES).order_by("-allocated_at").first()
        return Response({
            "pending_count": pending.count(),
            "pending": DriverTripSerializer(pending[:10], many=True).data,
            "active_trip": DriverTripSerializer(active).data if active else None,
            "trucks": TruckBriefSerializer(Truck.objects.filter(default_driver=request.user, is_active=True), many=True).data,
            "open_empty_legs": EmptyLeg.objects.filter(driver=request.user, status=EmptyLegStatus.OPEN).count(),
        })


class DriverTripListView(DriverView, ListAPIView):
    serializer_class = DriverTripSerializer

    def get_queryset(self):
        qs = _my_trips(self.request)
        state = self.request.query_params.get("state")
        if state == "pending":
            qs = qs.filter(status=TripStatus.ALLOCATED)
        elif state == "active":
            qs = qs.filter(status__in=[TripStatus.ALLOCATED, *TRIP_LIVE_STATUSES])
        elif state == "history":
            qs = qs.filter(status__in=[TripStatus.COMPLETED, TripStatus.CANCELLED])
        return qs.order_by("-allocated_at", "-created_at")


class DriverTripMixin(DriverView):
    lookup_field = "code"

    def get_queryset(self):
        return _my_trips(self.request)

    def detail(self, trip):
        return Response(DriverTripDetailSerializer(self.get_queryset().get(pk=trip.pk)).data)


class DriverTripDetailView(DriverTripMixin, RetrieveAPIView):
    serializer_class = DriverTripDetailSerializer


class DriverTripRespondView(DriverTripMixin, GenericAPIView):
    serializer_class = RespondSerializer

    def post(self, request, code):
        trip = self.get_object()
        if trip.status != TripStatus.ALLOCATED or trip.driver_response != DriverResponse.PENDING:
            raise ValidationError({"detail": "This trip is not waiting for your response."})
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        trip.respond(s.validated_data["accept"], s.validated_data["reason"], user=request.user)
        if not s.validated_data["accept"]:
            return Response({"detail": "Trip declined. The operations team has been notified."})
        return self.detail(trip)


class DriverTripStatusView(DriverTripMixin, GenericAPIView):
    """Driver moves the trip along: loading → in transit ⇄ at border → arrived → completed."""

    serializer_class = TripMoveSerializer

    def post(self, request, code):
        trip = self.get_object()
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        allowed = DRIVER_NEXT_STATUS.get(trip.status, [])
        if d["status"] not in allowed:
            raise ValidationError({"status": f"From '{trip.get_status_display()}' you can go to: "
                                             + (", ".join(a.label for a in allowed) or "nothing (ask operations)") + "."})
        trip.advance(d["status"], place=d["place"], place_label=d["place_label"], note=d["note"],
                     user=request.user, lat=d["lat"], lng=d["lng"])
        return self.detail(trip)


class DriverTripCheckpointView(DriverTripMixin, GenericAPIView):
    """Report a major point reached (town, weighbridge, border). Cargo owners see the place name."""

    serializer_class = CheckpointSerializer

    def post(self, request, code):
        trip = self.get_object()
        if trip.status not in (TripStatus.LOADING, TripStatus.IN_TRANSIT, TripStatus.AT_BORDER, TripStatus.ARRIVED):
            raise ValidationError({"detail": "Checkpoints can be reported once the trip is under way."})
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        trip.checkpoint(place=d["place"], place_label=d["place_label"], note=d["note"], user=request.user, lat=d["lat"], lng=d["lng"])
        return self.detail(trip)


class DriverTripPositionsView(DriverTripMixin, GenericAPIView):
    """Batched GPS fixes from the driver's phone (staff dashboard only)."""

    serializer_class = PositionBatchSerializer
    throttle_scope = "positions"

    @transaction.atomic
    def post(self, request, code):
        trip = self.get_object()
        if trip.status not in TRIP_LIVE_STATUSES:
            # Tell the app to stop sharing: the trip is not under way (or is finished).
            return Response({"accepted": 0, "tracking": False})
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        fixes = sorted(s.validated_data["positions"], key=lambda p: p["recorded_at"])
        TripPosition.objects.bulk_create([
            TripPosition(trip=trip, driver=request.user, lat=Decimal(str(round(p["lat"], 6))), lng=Decimal(str(round(p["lng"], 6))),
                         speed_kmh=p.get("speed_kmh"), heading=p.get("heading"), accuracy_m=p.get("accuracy_m"),
                         recorded_at=p["recorded_at"])
            for p in fixes
        ])
        latest = fixes[-1]
        if trip.last_position_at is None or latest["recorded_at"] >= trip.last_position_at:
            Trip.objects.filter(pk=trip.pk).update(
                last_lat=Decimal(str(round(latest["lat"], 6))), last_lng=Decimal(str(round(latest["lng"], 6))),
                last_speed_kmh=latest.get("speed_kmh"), last_heading=latest.get("heading"),
                last_position_at=latest["recorded_at"],
            )
        return Response({"accepted": len(fixes), "tracking": True}, status=status.HTTP_201_CREATED)


class DriverDeliverView(DriverTripMixin, GenericAPIView):
    """Mark one consignment on the trip as handed over to the receiver."""

    def post(self, request, code, tracking_number):
        trip = self.get_object()
        if trip.status not in (TripStatus.ARRIVED, TripStatus.IN_TRANSIT, TripStatus.AT_BORDER):
            raise ValidationError({"detail": "Deliveries can be recorded once the trip is under way."})
        shipment = get_object_or_404(trip.shipments.exclude(status__in=CLOSED_STATUSES), tracking_number=tracking_number)
        note = str(request.data.get("note", ""))[:255] if hasattr(request.data, "get") else ""
        shipment.update_status(ShipmentStatus.DELIVERED, location=shipment.destination_name,
                               note=note or "Delivered to the receiver.", user=request.user)
        trip.log("note", status=trip.status, note=f"{shipment.tracking_number} delivered.", user=request.user)
        return self.detail(trip)


class DriverEmptyLegListView(DriverView, ListCreateAPIView):
    """A driver's own empty-leg offers ("going back empty from Mombasa on Friday")."""

    serializer_class = EmptyLegSerializer

    def get_queryset(self):
        return EmptyLeg.objects.filter(driver=self.request.user).select_related("truck", "trip", "driver").order_by("-created_at")

    def perform_create(self, serializer):
        truck = serializer.validated_data.get("truck")
        if truck is not None and truck.default_driver_id not in (None, self.request.user.pk):
            raise ValidationError({"truck_id": "That truck is assigned to another driver."})
        serializer.save(driver=self.request.user)


class DriverEmptyLegDetailView(DriverView, RetrieveUpdateDestroyAPIView):
    serializer_class = EmptyLegSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return EmptyLeg.objects.filter(driver=self.request.user).select_related("truck", "trip", "driver")

    def perform_update(self, serializer):
        if serializer.instance.status != EmptyLegStatus.OPEN:
            raise ValidationError({"detail": "Only open offers can be changed."})
        serializer.save()

    def perform_destroy(self, instance):
        # Keep the record (operations may be mid-match); just withdraw it.
        if instance.status == EmptyLegStatus.MATCHED:
            raise ValidationError({"detail": "This offer is already matched to a trip. Call operations to change it."})
        instance.status = EmptyLegStatus.WITHDRAWN
        instance.save(update_fields=["status", "updated_at"])
