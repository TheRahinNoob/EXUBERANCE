from __future__ import annotations

from django.urls import path

# ==================================================
# ORDERS
# ==================================================
from store.views.admin.orders import (
    AdminOrderListView,
    AdminOrderDetailView,
    AdminOrderStatusUpdateView,
    AdminOrderAuditView,
)

# ==================================================
# PRODUCTS
# ==================================================
from store.views.admin.products import (
    AdminProductListView,
    AdminProductDetailView,
    AdminProductBasicInfoUpdateView,
    AdminProductDeactivateView,
)

from store.views.admin.product_description import (
    AdminProductDescriptionUpdateView,
)

from store.views.admin.product_images import (
    AdminProductImageListCreateView,
    AdminProductImageDetailView,
)

from store.views.admin.product_variants import (
    AdminProductVariantListCreateView,
    AdminProductVariantBulkCreateView,
    AdminProductVariantDetailView,
)

from store.views.admin.product_attributes import (
    AdminProductAttributeListView,
    AdminProductAttributeDetailView,
    AdminProductAttributeReorderView,
)

from store.views.admin.product_attribute_definitions import (
    AdminProductAttributeDefinitionListView,
    AdminProductAttributeDefinitionDetailView,
)

# ==================================================
# CATEGORIES
# ==================================================
from store.views.admin.categories import (
    AdminCategoryTreeView,
    AdminCategoryListCreateView,
    AdminCategoryDetailView,
    AdminCategoryReorderView,
)

# ==================================================
# CMS — LANDING CORE
# ==================================================
from store.views.admin.cms.landing_blocks import (
    AdminLandingBlockListCreateView,
    AdminLandingBlockDetailView,
    AdminLandingBlockReorderView,
)

from store.views.admin.cms.hero_banners import (
    AdminHeroBannerListCreateView,
    AdminHeroBannerDetailView,
)

from store.views.admin.cms.landing_menu_items import (
    AdminLandingMenuItemListCreateView,
    AdminLandingMenuItemDetailView,
)

from store.views.admin.cms.featured_categories import (
    AdminFeaturedCategoryListCreateView,
    AdminFeaturedCategoryDetailView,
)

from store.views.admin.cms.hot_categories import (
    AdminHotCategoryListCreateView,
    AdminHotCategoryDetailView,
)

from store.views.admin.cms.hot_category_blocks import (
    AdminHotCategoryBlockListCreateView,
    AdminHotCategoryBlockDetailView,
    AdminHotCategoryBlockItemCreateView,
    AdminHotCategoryBlockItemReorderView,
    AdminHotCategoryBlockItemDeleteView,
)

from store.views.admin.cms.comfort_rails import (
    AdminComfortCategoryRailListCreateView,
    AdminComfortCategoryRailDetailView,
    AdminComfortCategoryRailImageUpdateView,
    AdminComfortCategoryRailProductView,
    AdminComfortCategoryRailReorderView,
)

# ==================================================
# CMS — COMFORT EDITORIAL
# ==================================================
from store.views.admin.cms.comfort_editorial import (
    AdminComfortEditorialBlockListCreateView,
    AdminComfortEditorialBlockDetailView,
    AdminComfortEditorialBlockReorderView,
)

# ==================================================
# APP NAMESPACE
# ==================================================
app_name = "admin_api"

# ==================================================
# URLPATTERNS — JWT-PROTECTED ADMIN API
# ==================================================
urlpatterns = [
    # ---------------- ORDERS ----------------
    path("orders/", AdminOrderListView.as_view()),
    path("orders/<int:pk>/", AdminOrderDetailView.as_view()),
    path("orders/<int:pk>/status/", AdminOrderStatusUpdateView.as_view()),
    path("orders/<int:pk>/audit/", AdminOrderAuditView.as_view()),

    # ---------------- PRODUCTS ----------------
    path("products/", AdminProductListView.as_view()),
    path("products/<int:pk>/basic/", AdminProductBasicInfoUpdateView.as_view()),
    path("products/<int:pk>/description/", AdminProductDescriptionUpdateView.as_view()),
    path("products/<int:pk>/deactivate/", AdminProductDeactivateView.as_view()),
    path("products/<int:pk>/images/", AdminProductImageListCreateView.as_view()),
    path("product-images/<int:image_id>/", AdminProductImageDetailView.as_view()),

    # ---------------- VARIANTS ----------------
    # Keep specific routes BEFORE generic product detail route.
    path("products/<int:pk>/variants/", AdminProductVariantListCreateView.as_view()),
    path("products/<int:pk>/variants/bulk/", AdminProductVariantBulkCreateView.as_view()),
    path("product-variants/<int:variant_id>/", AdminProductVariantDetailView.as_view()),

    # ---------------- ATTRIBUTES ----------------
    path("products/<int:pk>/attributes/", AdminProductAttributeListView.as_view()),
    path("products/<int:pk>/attributes/reorder/", AdminProductAttributeReorderView.as_view()),
    path("product-attributes/<int:pav_id>/", AdminProductAttributeDetailView.as_view()),
    path("attribute-definitions/", AdminProductAttributeDefinitionListView.as_view()),
    path("attribute-definitions/<int:pk>/", AdminProductAttributeDefinitionDetailView.as_view()),

    # Product detail (keep after subroutes)
    path("products/<int:pk>/", AdminProductDetailView.as_view()),

    # ---------------- CATEGORIES ----------------
    path("categories/tree/", AdminCategoryTreeView.as_view()),
    path("categories/reorder/", AdminCategoryReorderView.as_view()),
    path("categories/", AdminCategoryListCreateView.as_view()),
    path("categories/<int:pk>/", AdminCategoryDetailView.as_view()),

    # ---------------- CMS ----------------
    path("cms/hero-banners/", AdminHeroBannerListCreateView.as_view()),
    path("cms/hero-banners/<int:pk>/", AdminHeroBannerDetailView.as_view()),
    path("cms/landing-blocks/", AdminLandingBlockListCreateView.as_view()),
    path("cms/landing-blocks/<int:pk>/", AdminLandingBlockDetailView.as_view()),
    path("cms/landing-blocks/reorder/", AdminLandingBlockReorderView.as_view()),
    path("cms/landing-menu-items/", AdminLandingMenuItemListCreateView.as_view()),
    path("cms/landing-menu-items/<int:pk>/", AdminLandingMenuItemDetailView.as_view()),
    path("cms/featured-categories/", AdminFeaturedCategoryListCreateView.as_view()),
    path("cms/featured-categories/<int:pk>/", AdminFeaturedCategoryDetailView.as_view()),
    path("cms/hot-categories/", AdminHotCategoryListCreateView.as_view()),
    path("cms/hot-categories/<int:pk>/", AdminHotCategoryDetailView.as_view()),
    path("cms/hot-category-blocks/", AdminHotCategoryBlockListCreateView.as_view()),
    path("cms/hot-category-blocks/<int:pk>/", AdminHotCategoryBlockDetailView.as_view()),
    path("cms/hot-category-blocks/<int:pk>/items/", AdminHotCategoryBlockItemCreateView.as_view()),
    path("cms/hot-category-blocks/<int:pk>/items/reorder/", AdminHotCategoryBlockItemReorderView.as_view()),
    path("cms/hot-category-blocks/<int:pk>/items/<int:item_id>/", AdminHotCategoryBlockItemDeleteView.as_view()),
    path("cms/comfort-rails/", AdminComfortCategoryRailListCreateView.as_view()),
    path("cms/comfort-rails/<int:pk>/", AdminComfortCategoryRailDetailView.as_view()),
    path("cms/comfort-rails/<int:pk>/image/", AdminComfortCategoryRailImageUpdateView.as_view()),
    path("cms/comfort-rails/<int:pk>/products/", AdminComfortCategoryRailProductView.as_view()),
    path("cms/comfort-rails/<int:pk>/products/<int:product_id>/", AdminComfortCategoryRailProductView.as_view()),
    path("cms/comfort-rails/reorder/", AdminComfortCategoryRailReorderView.as_view()),
    path("cms/comfort-editorial/", AdminComfortEditorialBlockListCreateView.as_view()),
    path("cms/comfort-editorial/<int:pk>/", AdminComfortEditorialBlockDetailView.as_view()),
    path("cms/comfort-editorial/reorder/", AdminComfortEditorialBlockReorderView.as_view()),
]