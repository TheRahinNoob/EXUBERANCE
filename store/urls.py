from django.urls import path

# ==================================================
# LANDING PAGE — CMS & BLOCKS
# ==================================================
from store.views.landing_cms import LandingCMSAPIView
from store.views.landing import (
    LandingHeroBannerAPIView,
    LandingMenuAPIView,
    LandingFeaturedCategoriesAPIView,
    LandingComfortAPIView,
)
from store.views.landing_hot_categories import (
    LandingHotCategoriesAPIView,
)
from store.views.landing_comfort_editorial import (
    LandingComfortEditorialAPIView,
)

# ==================================================
# CATEGORY (PUBLIC)
# ==================================================
from store.views.category import (
    CategoryListAPIView,
    CategoryDetailAPIView,
    CategoryCardListAPIView,
)

# ==================================================
# PRODUCTS (PUBLIC)
# ==================================================
from store.views.product import (
    ProductListAPIView,
    ProductDetailAPIView,
    RelatedProductAPIView,
)

# ==================================================
# SEARCH
# ==================================================
from store.views.search import ProductSearchAPIView

# ==================================================
# ORDERS
# ==================================================
from store.views.order import (
    CreateOrderAPIView,
    OrderTrackingAPIView,
)

# ==================================================
# APP NAMESPACE
# ==================================================
app_name = "store"

# ==================================================
# URLPATTERNS — PUBLIC API ONLY
# ==================================================
urlpatterns = [

    # ==================================================
    # LANDING PAGE — CMS STRUCTURE (ORDER ONLY)
    # ==================================================
    path(
        "landing/cms/",
        LandingCMSAPIView.as_view(),
        name="landing-cms",
    ),

    # ==================================================
    # LANDING PAGE — ATOMIC BLOCK DATA
    # ==================================================
    path(
        "landing/banners/",
        LandingHeroBannerAPIView.as_view(),
        name="landing-hero-banners",
    ),
    path(
        "landing/menu/",
        LandingMenuAPIView.as_view(),
        name="landing-menu",
    ),
    path(
        "landing/featured-categories/",
        LandingFeaturedCategoriesAPIView.as_view(),
        name="landing-featured-categories",
    ),
    path(
        "landing/hot-categories/",
        LandingHotCategoriesAPIView.as_view(),
        name="landing-hot-categories",
    ),
    path(
        "landing/comfort/",
        LandingComfortAPIView.as_view(),
        name="landing-comfort-rail",
    ),
    path(
        "landing/comfort-editorial/",
        LandingComfortEditorialAPIView.as_view(),
        name="landing-comfort-editorial",
    ),

    # ==================================================
    # CATEGORY (PUBLIC)
    # ==================================================
    path(
        "categories/",
        CategoryListAPIView.as_view(),
        name="category-list",
    ),
    path(
        "categories/cards/",
        CategoryCardListAPIView.as_view(),
        name="category-cards",
    ),
    path(
        "categories/<slug:slug>/",
        CategoryDetailAPIView.as_view(),
        name="category-detail",
    ),

    # ==================================================
    # PRODUCTS (PUBLIC)
    # ==================================================
    path(
        "products/",
        ProductListAPIView.as_view(),
        name="product-list",
    ),
    path(
        "products/<slug:slug>/",
        ProductDetailAPIView.as_view(),
        name="product-detail",
    ),
    path(
        "products/<slug:slug>/related/",
        RelatedProductAPIView.as_view(),
        name="product-related",
    ),

    # ==================================================
    # SEARCH
    # ==================================================
    path(
        "search/",
        ProductSearchAPIView.as_view(),
        name="product-search",
    ),

    # ==================================================
    # ORDERS
    # ==================================================
    path(
        "orders/",
        CreateOrderAPIView.as_view(),
        name="order-create",
    ),
    path(
        "orders/track/",
        OrderTrackingAPIView.as_view(),
        name="order-track",
    ),
]