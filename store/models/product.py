from django.db import models
from django.core.exceptions import ValidationError

from .category import Category


# ==================================================
# PRODUCT (CORE)
# ==================================================
class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    categories = models.ManyToManyField(
        Category,
        related_name="products",
        limit_choices_to={"is_active": True},
        blank=True,
        help_text="Products may belong to multiple categories",
    )

    short_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short marketing description",
    )

    description = models.TextField(
        blank=True,
        help_text="Full product description",
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    main_image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.name


# ==================================================
# PRODUCT VARIANT (SIZE / COLOR / STOCK)
# ==================================================
class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
        ("XL", "Extra Large"),
        ("XXL", "Double XL"),
    ]

    product = models.ForeignKey(
        Product,
        related_name="variants",
        on_delete=models.CASCADE,
    )

    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    color = models.CharField(max_length=50)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "size", "color")
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["stock"]),
        ]

    def __str__(self) -> str:
        return f"{self.product} | {self.size} | {self.color}"


# ==================================================
# PRODUCT ATTRIBUTE (GLOBAL DEFINITION)
# ==================================================
# ==================================================
# PRODUCT ATTRIBUTE (GLOBAL DEFINITION)
# ==================================================
class ProductAttribute(models.Model):
    """
    Global reusable attribute definitions.

    Examples:
    - Fabric
    - GSM
    - Fit
    - Composition

    DESIGN:
    - Attributes are NEVER hard-deleted
    - Soft delete via `is_active`
    - Existing products remain valid forever
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Attribute name (e.g. Fabric, GSM, Fit)",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Global display order",
    )

    # 🔥 SOFT DELETE FLAG
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive attributes are archived (not deletable)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ordering", "name")
        verbose_name = "Product Attribute"
        verbose_name_plural = "Product Attributes"
        indexes = [
            models.Index(fields=["ordering"]),
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Attribute name cannot be empty."})

        # Normalize casing
        self.name = self.name.strip().title()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        status = "active" if self.is_active else "archived"
        return f"{self.name} ({status})"


# ==================================================
# PRODUCT ATTRIBUTE VALUE (PER PRODUCT)
# ==================================================
class ProductAttributeValue(models.Model):
    """
    Assigns a concrete value of an attribute to a product.

    RULES:
    - One attribute per product
    - Attribute is IMMUTABLE once assigned
    - Ordering is product-scoped
    """

    product = models.ForeignKey(
        Product,
        related_name="attribute_values",
        on_delete=models.CASCADE,
    )

    attribute = models.ForeignKey(
        ProductAttribute,
        related_name="values",
        on_delete=models.PROTECT,  # 🔒 critical safety
    )

    value = models.CharField(
        max_length=255,
        help_text="Value (e.g. 100% Cotton, 180 GSM)",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Display order within product page",
    )

    class Meta:
        ordering = ("ordering", "id")
        unique_together = ("product", "attribute")
        verbose_name = "Product Attribute Value"
        verbose_name_plural = "Product Attribute Values"
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["attribute"]),
            models.Index(fields=["ordering"]),
        ]

    def clean(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError({"value": "Attribute value cannot be empty."})

        self.value = self.value.strip()

    def save(self, *args, **kwargs):
        self.full_clean()  # enforce validation
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.product} | {self.attribute}: {self.value}"
