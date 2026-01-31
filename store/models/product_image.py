from django.db import models


class ProductImage(models.Model):
    """
    Product image model.

    DESIGN:
    - Multiple images per product
    - One optional primary image
    - Ordered
    - Soft future-ready (CDN, optimization, etc.)
    """

    product = models.ForeignKey(
        "store.Product",
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="product_images/",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    is_primary = models.BooleanField(
        default=False,
        help_text="Primary image used as main product image",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Lower number = shown first",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["ordering", "id"]
        indexes = [
            models.Index(fields=["product", "is_primary"]),
        ]

    def __str__(self):
        return f"Image #{self.id} for {self.product.name}"
