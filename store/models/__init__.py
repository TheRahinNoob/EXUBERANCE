"""
store.models

Central registry of all database models.

RULES:
- Every model intended for cross-app imports MUST be exposed here
- Prevents circular imports
- Enables clean imports like:
    from store.models import Order, Product
"""

# ==================================================
# CORE CATALOG
# ==================================================
from .category import Category

# ==================================================
# PRODUCTS
# ==================================================
from .product import (
    Product,
    ProductVariant,
    ProductAttribute,
    ProductAttributeValue,
)

from .product_image import ProductImage

# ==================================================
# ORDERS
# ==================================================
from .order import Order, OrderItem
from .order_status_audit import OrderStatusAuditLog

# ==================================================
# LANDING / CMS
# ==================================================
from .hero_banner import HeroBanner

from .landing import (
    LandingMenuItem,
    FeaturedCategory,
    HotCategory,
    HotCategoryBlock,
    HotCategoryBlockItem,
)

from .landing_comfort import ComfortCategoryRail
from .landing_block import LandingBlock

# ==================================================
# EXPLICIT EXPORT CONTROL
# ==================================================
__all__ = [
    # Core
    "Category",

    # Products
    "Product",
    "ProductImage",
    "ProductVariant",
    "ProductAttribute",
    "ProductAttributeValue",

    # Orders
    "Order",
    "OrderItem",
    "OrderStatusAuditLog",

    # Landing / CMS
    "HeroBanner",
    "LandingMenuItem",
    "FeaturedCategory",
    "HotCategory",
    "HotCategoryBlock",
    "HotCategoryBlockItem",
    "ComfortCategoryRail",
    "LandingBlock",
]
