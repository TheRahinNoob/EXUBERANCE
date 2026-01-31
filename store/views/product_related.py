from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import models
from django.db.models import Count

from store.models import Product
from store.serializers import ProductListSerializer



class RelatedProductAPIView(APIView):
    """
    Returns products related by category similarity.
    """

    def get(self, request, slug):
        try:
            product = Product.objects.prefetch_related(
                "categories"
            ).get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Response([], status=200)

        categories = product.categories.all()

        if not categories.exists():
            return Response([], status=200)

        related_qs = (
            Product.objects.filter(
                is_active=True,
                categories__in=categories,
            )
            .exclude(id=product.id)
            .annotate(
                shared_categories=Count(
                    "categories",
                    filter=models.Q(categories__in=categories),
                )
            )
            .order_by(
                "-shared_categories",
                "-created_at",
            )
            .distinct()[:8]
        )

        serializer = ProductListSerializer(
            related_qs,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)
