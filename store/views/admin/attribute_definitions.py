from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from store.models import ProductAttribute
from store.services.product_attribute_definition_service import (
    create_attribute_definition,
    update_attribute_definition,
    delete_attribute_definition,
)


class AdminAttributeDefinitionListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        attrs = ProductAttribute.objects.all().order_by("ordering", "name")

        return Response(
            [
                {
                    "id": a.id,
                    "name": a.name,
                    "ordering": a.ordering,
                }
                for a in attrs
            ]
        )

    def post(self, request):
        data = request.data or {}

        try:
            attr = create_attribute_definition(
                name=data.get("name"),
                ordering=data.get("ordering", 0),
            )
        except ValidationError:
            raise

        return Response(
            {
                "id": attr.id,
                "name": attr.name,
                "ordering": attr.ordering,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminAttributeDefinitionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk: int):
        attr = get_object_or_404(ProductAttribute, pk=pk)
        data = request.data or {}

        try:
            attr = update_attribute_definition(
                attribute=attr,
                name=data.get("name"),
                ordering=data.get("ordering"),
            )
        except ValidationError:
            raise

        return Response(
            {
                "id": attr.id,
                "name": attr.name,
                "ordering": attr.ordering,
            }
        )

    def delete(self, request, pk: int):
        attr = get_object_or_404(ProductAttribute, pk=pk)
        delete_attribute_definition(attribute=attr)
        return Response(status=status.HTTP_204_NO_CONTENT)
