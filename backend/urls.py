from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # =====================================
    # DJANGO ADMIN (SYSTEM / FALLBACK)
    # =====================================
    path("admin/", admin.site.urls),

    # =====================================
    # DJANGO SUMMERNOTE (CMS EDITOR)
    # =====================================
    path("summernote/", include("django_summernote.urls")),

    # =====================================
    # PUBLIC & USER APIs
    # =====================================
    path("api/", include("store.urls")),

    # =====================================
    # ADMIN APIs (NEXT.JS ADMIN PANEL)
    # =====================================
    path("api/admin/", include("store.admin_urls")),
]

# =====================================
# MEDIA FILES (DEVELOPMENT ONLY)
# =====================================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
