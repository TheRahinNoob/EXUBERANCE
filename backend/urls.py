from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ==================================================
# JWT AUTH ENDPOINTS (ADMIN LOGIN)
# ==================================================
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # ==================================================
    # DJANGO ADMIN (SESSION + CSRF — BACKUP ONLY)
    # ==================================================
    path("admin/", admin.site.urls),

    # ==================================================
    # DJANGO SUMMERNOTE (CMS EDITOR)
    # ==================================================
    path("summernote/", include("django_summernote.urls")),

    # ==================================================
    # 🔐 JWT AUTH — NEXT.JS ADMIN
    # ==================================================
    # POST username + password → access + refresh
    path(
        "api/auth/login/",
        TokenObtainPairView.as_view(),
        name="jwt-login",
    ),

    # POST refresh → new access token
    path(
        "api/auth/refresh/",
        TokenRefreshView.as_view(),
        name="jwt-refresh",
    ),

    # ==================================================
    # PUBLIC APIs (STORE / USER)
    # ==================================================
    path("api/", include("store.urls")),

    # ==================================================
    # ADMIN APIs (JWT-PROTECTED)
    # ==================================================
    path("api/admin/", include("store.admin_urls")),
]

# ==================================================
# MEDIA FILES (DEVELOPMENT ONLY)
# ==================================================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
