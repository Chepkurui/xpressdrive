from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ContactMessageSerializer


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class ContactCreateView(CreateAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ContactMessageSerializer
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("website"):
            serializer.save()
        # Same response for bots and humans.
        return Response({"detail": "Thank you. Our team will get back to you shortly."}, status=status.HTTP_201_CREATED)
