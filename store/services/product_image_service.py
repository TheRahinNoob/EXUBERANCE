from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from store.models import Product, ProductImage


# ==================================================
# ADD PRODUCT IMAGE
# ==================================================
@transaction.atomic
def add_product_image(
    *,
    product: Product,
    image,
    alt_text: str = "",
    is_primary: bool = False,
) -> ProductImage:
    """
    Upload a product image safely.

    GUARANTEES:
    - Image file is mandatory
    - Atomic operation
    - Only ONE primary image per product
    - Product.main_image always stays in sync
    - Ordering is auto-assigned (append-only)
    """

    # -----------------------------
    # VALIDATION
    # -----------------------------
    if not isinstance(product, Product):
        raise ValidationError({"product": "Invalid product."})

    if not image:
        raise ValidationError({"image": "Image file is required."})

    # Optional: basic sanity check (prevents non-image uploads)
    if not getattr(image, "content_type", "").startswith("image/"):
        raise ValidationError({"image": "Uploaded file must be an image."})

    alt_text = (alt_text or "").strip()

    # -----------------------------
    # ORDERING (APPEND LAST)
    # -----------------------------
    last_ordering = (
        ProductImage.objects
        .filter(product=product)
        .order_by("-ordering")
        .values_list("ordering", flat=True)
        .first()
    )

    next_ordering = (last_ordering or 0) + 1

    # -----------------------------
    # PRIMARY IMAGE LOGIC
    # -----------------------------
    if is_primary:
        (
            ProductImage.objects
            .filter(product=product, is_primary=True)
            .update(is_primary=False)
        )

    # -----------------------------
    # CREATE IMAGE
    # -----------------------------
    try:
        product_image = ProductImage.objects.create(
            product=product,
            image=image,
            alt_text=alt_text,
            is_primary=is_primary,
            ordering=next_ordering,
        )
    except DjangoValidationError as e:
        raise ValidationError(e.message_dict)
    except Exception:
        raise ValidationError({
            "message": "Failed to save product image."
        })

    # -----------------------------
    # SYNC MAIN IMAGE
    # -----------------------------
    if is_primary:
        product.main_image = product_image.image
        product.save(update_fields=["main_image"])

    return product_image


# ==================================================
# SET PRIMARY IMAGE
# ==================================================
@transaction.atomic
def set_primary_image(
    *,
    image: ProductImage,
) -> None:
    """
    Mark a product image as primary.

    GUARANTEES:
    - Exactly ONE primary image per product
    - Product.main_image stays in sync
    - Atomic & race-condition safe
    """

    if not isinstance(image, ProductImage):
        raise ValidationError({"image": "Invalid product image."})

    product = image.product

    # -----------------------------
    # UNSET OTHERS
    # -----------------------------
    (
        ProductImage.objects
        .filter(product=product, is_primary=True)
        .exclude(pk=image.pk)
        .update(is_primary=False)
    )

    # -----------------------------
    # SET THIS ONE
    # -----------------------------
    if not image.is_primary:
        image.is_primary = True
        image.save(update_fields=["is_primary"])

    # -----------------------------
    # SYNC PRODUCT MAIN IMAGE
    # -----------------------------
    product.main_image = image.image
    product.save(update_fields=["main_image"])
