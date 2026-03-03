from __future__ import annotations

from django.db import models
from django.core.exceptions import ValidationError

from .category import Category


# ==================================================
# INTERNAL NORMALIZATION HELPERS
# ==================================================

def _collapse_ws(value: str) -> str:
    return " ".join(value.split())


def _normalize_size(value: object) -> str:
    """
    Normalizes sizes to reduce duplicates.

    Examples:
    - "  m " -> "M"
    - "  38  " -> "38"
    - "one   size" -> "one size" (kept as-is, not uppercased)
    - "38R" -> "38R"
    """
    token = _collapse_ws(str(value or "").strip())
    if token.isalpha():
        token = token.upper()
    return token


def _normalize_color(value: object) -> str:
    """
    Normalizes colors to reduce duplicates.

    Examples:
    - " blue " -> "Blue"
    - "deep   blue" -> "Deep Blue"
    - "" -> ""
    """
    token = _collapse_ws(str(value or "").strip())
    if not token:
        return ""
    return token.title()


def _normalize_hex_color(value: object) -> str:
    """
    Normalizes hex colors:
    - trims whitespace
    - uppercases
    - keeps empty string if missing

    Examples:
    - "  #ff00aa " -> "#FF00AA"
    - "" -> ""
    - None -> ""
    """
    return str(value or "").strip().upper()


def _is_valid_hex_color(value: str) -> bool:
    """
    Validates strict #RRGGBB format.
    """
    if not value or len(value) != 7 or not value.startswith("#"):
        return False
    allowed = "0123456789ABCDEF"
    return all(ch in allowed for ch in value[1:])


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

    def clean(self) -> None:
        # Optional hardening: keep product name clean
        if not self.name or not self.name.strip():
            raise ValidationError({"name": "Product name cannot be empty."})
        self.name = _collapse_ws(self.name.strip())

        # Optional: normalize slug whitespace (SlugField already validates format)
        if self.slug:
            self.slug = self.slug.strip()

        # Optional business rule:
        # old_price should not be less than price (if provided)
        if self.old_price is not None and self.old_price < self.price:
            raise ValidationError({"old_price": "Old price cannot be less than current price."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


# ==================================================
# PRODUCT VARIANT (SIZE / COLOR / STOCK)
# ==================================================

class ProductVariant(models.Model):
    """
    Variant model supports numeric + mixed sizes.
    Examples:
    - 38, 40, 42
    - S, M, L
    - One Size
    - 38R
    """

    product = models.ForeignKey(
        Product,
        related_name="variants",
        on_delete=models.CASCADE,
    )

    # ✅ No choices here so you can use numeric/mixed sizes per product
    size = models.CharField(max_length=32)
    color = models.CharField(max_length=50)

    # ✅ New: optional hex code for UI color swatch
    # Stored as strict "#RRGGBB" (uppercase), or "" if unknown.
    color_hex = models.CharField(
        max_length=7,
        blank=True,
        default="",
        help_text="Optional hex color code like #RRGGBB (used for color swatch on site).",
    )

    stock = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"],
                name="uniq_product_size_color",
            )
        ]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["stock"]),
            models.Index(fields=["size"]),
            models.Index(fields=["color"]),
            models.Index(fields=["color_hex"]),
        ]

    def clean(self) -> None:
        # Normalize
        self.size = _normalize_size(self.size)
        self.color = _normalize_color(self.color)
        self.color_hex = _normalize_hex_color(self.color_hex)

        # Validate required
        if not self.size:
            raise ValidationError({"size": "Size is required."})

        if not self.color:
            raise ValidationError({"color": "Color is required."})

        # Extra hardening
        if len(self.size) > 32:
            raise ValidationError({"size": "Size is too long."})
        if len(self.color) > 50:
            raise ValidationError({"color": "Color is too long."})

        # Validate hex format if provided
        if self.color_hex and not _is_valid_hex_color(self.color_hex):
            raise ValidationError({"color_hex": "Hex color must be in the format #RRGGBB."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.product} | {self.size} | {self.color}"


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
        self.name = _collapse_ws(self.name.strip()).title()

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
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attribute"],
                name="uniq_product_attribute_value",
            )
        ]
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

        self.value = _collapse_ws(self.value.strip())

    def save(self, *args, **kwargs):
        self.full_clean()  # enforce validation
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.product} | {self.attribute}: {self.value}"