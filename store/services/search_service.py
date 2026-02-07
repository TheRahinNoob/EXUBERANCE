from django.db import connection
from django.db.models import QuerySet, Q
from django.utils.timezone import now

from django.contrib.postgres.search import (
    SearchVector,
    SearchQuery,
    SearchRank,
)

from store.models import Product, Category


# ==================================================
# INTERNAL: CATEGORY + DESCENDANT RESOLVER
# (NORMAL + CAMPAIGN CATEGORIES — UNIFIED)
# ==================================================
def _resolve_category_ids(slugs: list[str]) -> set[int]:
    """
    Resolve category IDs including all descendants.

    DESIGN RULES (NON-NEGOTIABLE):
    - Categories are the ONLY taxonomy
    - Campaigns are categories with is_campaign=True
    - Expired / inactive campaigns must NOT return products
    - Parent category automatically includes all descendants
    """

    if not slugs:
        return set()

    current_time = now()

    roots = (
        Category.objects
        .filter(
            slug__in=slugs,
            is_active=True,
        )
        .filter(
            Q(is_campaign=False) |
            Q(
                is_campaign=True,
                starts_at__lte=current_time,
                ends_at__gte=current_time,
            )
        )
        .only("id")
    )

    resolved: set[int] = set()
    stack = list(roots)

    while stack:
        node = stack.pop()

        if node.id in resolved:
            continue

        resolved.add(node.id)

        stack.extend(
            node.children.filter(is_active=True).only("id")
        )

    return resolved


# ==================================================
# MAIN SEARCH SERVICE (AUTHORITATIVE & FUTURE-SAFE)
# ==================================================
def search_products(
    *,
    query: str | None = None,
    category_slug: str | None = None,     # backward compatibility
    categories: list[str] | None = None,  # multi-category + campaigns
    min_price: int | None = None,
    max_price: int | None = None,
    ordering: str | None = None,
) -> QuerySet:
    """
    SINGLE SOURCE OF TRUTH for product discovery.

    GUARANTEES:
    - Categories are the ONLY taxonomy (campaigns included)
    - Campaign categories are DATE-SAFE
    - UNION filtering (not intersection)
    - Parent categories include descendants
    - Ranked full-text search (Postgres)
    - SQLite-safe fallback search (dev)
    - Deterministic ordering (SEO-safe)
    - Pagination-safe
    - No duplicate rows
    """

    qs = Product.objects.filter(is_active=True)

    # -------------------------------------------------
    # FULL-TEXT SEARCH
    # -------------------------------------------------
    if query:
        query = query.strip()

        if connection.vendor == "postgresql":
            # 🔥 Production-grade ranked full-text search
            vector = (
                SearchVector("name", weight="A") +
                SearchVector("short_description", weight="B") +
                SearchVector("description", weight="C")
            )

            search_query = SearchQuery(query)

            qs = (
                qs.annotate(rank=SearchRank(vector, search_query))
                  .filter(rank__gt=0.1)
                  .order_by("-rank", "-created_at")
            )
        else:
            # 🧪 SQLite-safe fallback (local dev)
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(short_description__icontains=query) |
                Q(description__icontains=query)
            ).order_by("-created_at")

    # -------------------------------------------------
    # CATEGORY / CAMPAIGN FILTERING (UNIFIED)
    # -------------------------------------------------
    slugs: list[str] = []

    if categories:
        slugs.extend(categories)

    if category_slug:
        slugs.append(category_slug)

    if slugs:
        category_ids = _resolve_category_ids(list(set(slugs)))

        # 🚫 Invalid / expired campaign → empty result
        if not category_ids:
            return Product.objects.none()

        qs = qs.filter(categories__id__in=category_ids)

    # -------------------------------------------------
    # PRICE FILTERS
    # -------------------------------------------------
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)

    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    # -------------------------------------------------
    # ORDERING (SEO-SAFE & DETERMINISTIC)
    # -------------------------------------------------
    if ordering == "price_asc":
        qs = qs.order_by("price", "-created_at")
    elif ordering == "price_desc":
        qs = qs.order_by("-price", "-created_at")
    elif ordering == "newest":
        qs = qs.order_by("-created_at")

    # DISTINCT REQUIRED DUE TO M2M
    return qs.distinct()
