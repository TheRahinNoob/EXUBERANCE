from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError

from django.db import DatabaseError
import traceback
import logging

from store.models import Order
from store.serializers import (
    OrderCreateSerializer,
    OrderTrackingSerializer,
)

logger = logging.getLogger(__name__)

# ==================================================
# CREATE ORDER (CHECKOUT)
# ==================================================
class CreateOrderAPIView(APIView):
    """
    HTTP boundary for order creation.

    Responsibilities:
    - Validate input via serializer
    - Persist order atomically (handled by serializer/service)
    - Return safe, user-facing responses
    - NEVER swallow unexpected exceptions silently
    """

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            order = serializer.save()

        except ValidationError as e:
            # Client-side error (bad input)
            return Response(
                {"errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except DatabaseError as e:
            # Database-level failure (deadlock, constraint, etc.)
            logger.error(
                "Database error while creating order",
                exc_info=True,
            )
            return Response(
                {
                    "detail": (
                        "Unable to process your order right now. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            # 🔥 CRITICAL FIX: DO NOT SWALLOW TRACEBACK
            logger.critical(
                "Unhandled exception during order creation",
                exc_info=True,
            )

            # Also print traceback explicitly (dev-safe)
            traceback.print_exc()

            return Response(
                {
                    "detail": (
                        "Unexpected error occurred while placing order."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # -----------------------------
        # SUCCESS
        # -----------------------------
        return Response(
            {
                "reference": order.reference,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ==================================================
# TRACK ORDER (PUBLIC)
# ==================================================
class OrderTrackingAPIView(APIView):
    """
    Public order tracking endpoint.
    """

    def get(self, request):
        reference = request.query_params.get("reference")
        phone = request.query_params.get("phone")

        if not reference or not phone:
            return Response(
                {
                    "detail": (
                        "Order reference and phone number are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = (
                Order.objects
                .prefetch_related("items")
                .get(reference=reference, phone=phone)
            )
        except Order.DoesNotExist:
            raise NotFound(
                "No order found with the provided reference and phone."
            )

        serializer = OrderTrackingSerializer(order)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
