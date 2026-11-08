import re

from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAccountUser
from apps.data.models import ACTIVE_STATUSES, CLOSED_STATUSES, Shipment, ShipmentStatus
from .serializers import (
    PublicTrackingSerializer,
    ShipmentDetailSerializer,
    ShipmentListSerializer,
    ShipmentWriteSerializer,
)

TRACKING_RE = re.compile(r"^(XD|WD)[A-Z0-9]{10}$")  # WD: bookings made before the XpressDrive rename
ORDERING_FIELDS = {"created_at", "-created_at", "updated_at", "-updated_at", "status", "-status"}


class OwnedShipmentMixin:
    """Object-level authorization: every query is scoped to the requesting
    user, so another customer's shipment is indistinguishable from a
    non-existent one (404, no IDOR)."""

    permission_classes = [IsAccountUser]
    lookup_field = "tracking_number"

    def get_queryset(self):
        return Shipment.objects.filter(owner=self.request.user).select_related("parent").prefetch_related("parts", "parent__parts")


class ShipmentListCreateView(OwnedShipmentMixin, ListCreateAPIView):
    def get_serializer_class(self):
        return ShipmentWriteSerializer if self.request.method == "POST" else ShipmentListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        state = params.get("state")
        if state == "active":
            qs = qs.filter(status__in=ACTIVE_STATUSES)
        elif state == "closed":
            qs = qs.filter(status__in=CLOSED_STATUSES)
        # One status, or several comma-separated (the app's stage pills, e.g. "in_transit,at_border").
        status_param = params.get("status")
        if status_param:
            wanted = set(status_param.split(",")[:len(ShipmentStatus.values)])
            if not wanted <= set(ShipmentStatus.values):
                raise ValidationError({"status": "Unknown status."})
            qs = qs.filter(status__in=wanted)
        mode = params.get("mode")
        if mode:
            qs = qs.filter(mode=mode)
        q = (params.get("q") or "").strip()[:60]
        if q:
            qs = qs.filter(
                Q(tracking_number__icontains=q) | Q(description__icontains=q) | Q(consignee_name__icontains=q)
            )
        ordering = params.get("ordering")
        if ordering in ORDERING_FIELDS:
            qs = qs.order_by(ordering)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipment = serializer.save(owner=request.user)
        return Response(ShipmentDetailSerializer(shipment).data, status=status.HTTP_201_CREATED)


class ShipmentDetailView(OwnedShipmentMixin, RetrieveUpdateAPIView):
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return super().get_queryset().prefetch_related("events")

    def get_serializer_class(self):
        return ShipmentWriteSerializer if self.request.method == "PATCH" else ShipmentDetailSerializer

    def update(self, request, *args, **kwargs):
        shipment = self.get_object()
        if not shipment.is_editable_by_customer:
            raise ValidationError({"detail": "This booking can no longer be edited because it has been confirmed. Contact us to make changes."})
        serializer = self.get_serializer(shipment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ShipmentDetailSerializer(self.get_queryset().get(pk=shipment.pk)).data)


class ShipmentCancelView(OwnedShipmentMixin, GenericAPIView):
    def post(self, request, tracking_number):
        shipment = self.get_object()
        if not shipment.is_editable_by_customer:
            raise ValidationError({"detail": "Only bookings that have not been confirmed yet can be cancelled. Contact us to cancel."})
        shipment.update_status(ShipmentStatus.CANCELLED, note="Cancelled by customer.", user=request.user)
        return Response(ShipmentDetailSerializer(shipment).data)


class DashboardSummaryView(APIView):
    permission_classes = [IsAccountUser]

    def get(self, request):
        qs = Shipment.objects.filter(owner=request.user)
        agg = qs.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status__in=ACTIVE_STATUSES)),
            delivered=Count("id", filter=Q(status=ShipmentStatus.DELIVERED)),
            awaiting_payment=Count("id", filter=Q(payment_status="unpaid")),
            arrived=Count("id", filter=Q(status=ShipmentStatus.ARRIVED)),
            total_charges_usd=Sum("charge_usd", filter=~Q(status=ShipmentStatus.CANCELLED)),
        )
        by_status = {row["status"]: row["n"] for row in qs.values("status").annotate(n=Count("id"))}
        recent = ShipmentListSerializer(qs.select_related("parent").prefetch_related("parts", "parent__parts")[:5], many=True).data
        return Response({**agg, "by_status": by_status, "recent": recent})


class PublicTrackView(RetrieveAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicTrackingSerializer
    throttle_scope = "track"

    def get_object(self):
        number = self.kwargs["tracking_number"].strip().upper()
        if not TRACKING_RE.match(number):
            raise NotFound("No booking found with that tracking number.")
        shipment = Shipment.objects.prefetch_related("events").filter(tracking_number=number).first()
        if shipment is None:
            raise NotFound("No booking found with that tracking number.")
        return shipment
