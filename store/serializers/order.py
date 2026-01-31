from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils.timezone import localtime

from store.models import (
    Order,
    OrderItem,
    ProductVariant,
    OrderStatusAuditLog,
)

from store.services.order_service import create_order


# ==================================================
# ORDER CREATION — INPUT
# ==================================================
class OrderItemInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20)
    address = serializers.CharField()
    items = OrderItemInputSerializer(many=True)

    def validate(self, data):
        items = data.get("items")

        if not items:
            raise ValidationError({
                "items": "Order must contain at least one product."
            })

        variant_ids = {item["variant_id"] for item in items}

        existing_ids = set(
            ProductVariant.objects
            .filter(id__in=variant_ids)
            .values_list("id", flat=True)
        )

        invalid_ids = variant_ids - existing_ids
        if invalid_ids:
            raise ValidationError({
                "variant_id": (
                    "Invalid product variant(s): "
                    f"{sorted(invalid_ids)}"
                )
            })

        return data

    def create(self, validated_data):
        return create_order(
            name=validated_data["name"],
            phone=validated_data["phone"],
            address=validated_data["address"],
            items=validated_data["items"],
        )


# ==================================================
# ORDER TRACKING — PUBLIC & SAFE
# ==================================================
class OrderItemTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "product_name",
            "size",
            "color",
            "price",
            "quantity",
        )


class OrderStatusLogSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusAuditLog
        fields = (
            "from_status",
            "to_status",
            "created_at",
        )

    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()


class OrderTrackingSerializer(serializers.ModelSerializer):
    items = OrderItemTrackingSerializer(many=True, read_only=True)
    status_history = OrderStatusLogSerializer(
        many=True,
        source="status_logs",
        read_only=True,
    )
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "reference",
            "status",
            "total_price",
            "created_at",
            "items",
            "status_history",
        )

    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()
