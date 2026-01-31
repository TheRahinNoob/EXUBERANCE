"""
CMS Block Resolver for Landing Page

SINGLE SOURCE OF TRUTH for CMS serialization.

This module is responsible ONLY for:
- Translating LandingBlock DB rows
- Into lightweight, frontend-safe CMS payloads
"""

from typing import Optional, Dict, Any


# ==================================================
# BLOCK TYPE CONSTANTS (FRONTEND CONTRACT)
# ==================================================
BLOCK_HERO = "hero"
BLOCK_MENU = "menu"
BLOCK_FEATURED = "featured"
BLOCK_HOT = "hot"
BLOCK_COMFORT_BLOCK = "comfort_block"
BLOCK_COMFORT_RAIL = "comfort_rail"


# ==================================================
# PUBLIC API
# ==================================================
def build_block_payload(block) -> Optional[Dict[str, Any]]:
    """
    Build a lightweight CMS payload for a single landing block.

    HARD RULES:
    - IDs only (NO heavy data)
    - Must be frontend-safe
    - Invalid blocks are skipped silently (with logs)
    """

    if not block or not getattr(block, "block_type", None):
        _log("INVALID_BLOCK_OBJECT", block_id=getattr(block, "id", None))
        return None

    resolver = _BLOCK_RESOLVERS.get(block.block_type)

    if not resolver:
        _log("UNKNOWN_BLOCK_TYPE", block_id=block.id, block_type=block.block_type)
        return None

    try:
        payload = resolver(block)
    except Exception as exc:
        _log(
            "BLOCK_RESOLVER_EXCEPTION",
            block_id=block.id,
            block_type=block.block_type,
            error=str(exc),
        )
        return None

    if not payload or payload.get("type") != block.block_type:
        _log(
            "BLOCK_PAYLOAD_INVALID",
            block_id=block.id,
            block_type=block.block_type,
        )
        return None

    return payload


# ==================================================
# BLOCK RESOLVERS (ONE PER TYPE)
# ==================================================
def _resolve_hero(block):
    return {"type": BLOCK_HERO}


def _resolve_menu(block):
    return {"type": BLOCK_MENU}


def _resolve_featured(block):
    return {"type": BLOCK_FEATURED}


def _resolve_hot(block):
    """
    🔥 HOT CATEGORIES BLOCK (COLLECTIVE)
    """

    if not block.hot_category_block:
        _log("HOT_CATEGORY_BLOCK_MISSING", block_id=block.id)
        return None

    return {
        "type": BLOCK_HOT,
        "hot_category_block_id": block.hot_category_block.pk,
    }


def _resolve_comfort_block(block):
    """
    🧠 COMFORT EDITORIAL BLOCK

    NOTE:
    - Only emits the editorial block ID
    - Actual content is fetched via atomic API
    """

    if not block.comfort_editorial_block:
        _log("COMFORT_EDITORIAL_BLOCK_MISSING", block_id=block.id)
        return None

    return {
        "type": BLOCK_COMFORT_BLOCK,
        "comfort_editorial_block_id": block.comfort_editorial_block.pk,
    }


def _resolve_comfort_rail(block):
    """
    🧵 COMFORT CATEGORY RAIL
    """

    if not block.comfort_rail:
        _log("COMFORT_RAIL_MISSING", block_id=block.id)
        return None

    return {
        "type": BLOCK_COMFORT_RAIL,
        "comfort_rail_id": block.comfort_rail.pk,
    }


# ==================================================
# RESOLVER REGISTRY (EXTENSION POINT)
# ==================================================
_BLOCK_RESOLVERS = {
    BLOCK_HERO: _resolve_hero,
    BLOCK_MENU: _resolve_menu,
    BLOCK_FEATURED: _resolve_featured,
    BLOCK_HOT: _resolve_hot,
    BLOCK_COMFORT_BLOCK: _resolve_comfort_block,
    BLOCK_COMFORT_RAIL: _resolve_comfort_rail,
}


# ==================================================
# INTERNAL LOGGER (DEV-SAFE)
# ==================================================
def _log(event: str, **data):
    """
    Lightweight internal logger.

    - Never raises
    - Safe for production
    - Easy to swap with structured logging later
    """
    try:
        print(f"[CMS:{event}]", data)
    except Exception:
        pass
