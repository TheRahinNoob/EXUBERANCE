from django.contrib import admin
from store.models import ProductAttribute


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "ordering")
    search_fields = ("name",)
    ordering = ("ordering",)
