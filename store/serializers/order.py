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
    city = serializers.CharField(max_length=120)  # ✅ Added city

    delivery_area = serializers.ChoiceField(
        choices=Order.DELIVERY_AREA_CHOICES
    )

    items = OrderItemInputSerializer(many=True)

    # ----------------------------------------------
    # VALIDATION
    # ----------------------------------------------
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

    # ----------------------------------------------
    # CREATE ORDER (SERVICE LAYER)
    # ----------------------------------------------
    def create(self, validated_data):
        return create_order(
            name=validated_data["name"],
            phone=validated_data["phone"],
            address=validated_data["address"],
            city=validated_data["city"],  # ✅ Now included
            delivery_area=validated_data["delivery_area"],
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

    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    delivery_charge = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    total_price = serializers.SerializerMethodField()
    
    city = serializers.CharField(read_only=True)  # ✅ Optional: expose city in tracking

    class Meta:
        model = Order
        fields = (
            "reference",
            "status",
            "delivery_area",
            "city",  # ✅ include city
            "subtotal",
            "delivery_charge",
            "total_price",
            "created_at",
            "items",
            "status_history",
        )

    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()

    def get_total_price(self, obj):
        return str(obj.total_price)
