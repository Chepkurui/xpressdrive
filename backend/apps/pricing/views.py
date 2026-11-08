from dataclasses import asdict

from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.data.models import ShippingRate
from .serializers import EstimateRequestSerializer, EstimateResponseSerializer, ShippingRateSerializer
from .services import calculate_estimate

DISCLAIMER = (
    "Indicative estimate only. Final charges are confirmed when we quote your booking for the exact route "
    "and are adjusted to the weight and volume measured at loading. Excludes customs duties and taxes, "
    "border clearing agent fees, insurance and storage."
)


class ShippingRateListView(ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ShippingRateSerializer
    pagination_class = None
    queryset = ShippingRate.objects.filter(is_active=True)


class EstimateView(GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = EstimateRequestSerializer
    throttle_scope = "estimate"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        estimate = calculate_estimate(
            data["rate"],
            weight_kg=data["weight_kg"],
            quantity=data["quantity"],
            length_cm=data.get("length_cm"),
            width_cm=data.get("width_cm"),
            height_cm=data.get("height_cm"),
            containers=data["containers"],
        )
        payload = {**asdict(estimate), "disclaimer": DISCLAIMER}
        return Response(EstimateResponseSerializer(payload).data)
