"""
Custom permission classes for the Store app.

This file is the SINGLE source of truth for:
- Admin access control
- Future role-based permissions
- Next.js admin panel security

Rules:
- Frontend must NEVER be trusted
- All admin checks happen here
"""

from rest_framework.permissions import BasePermission


# ==================================================
# BASIC ADMIN PERMISSION
# ==================================================
class IsAdminUser(BasePermission):
    """
    Allows access only to authenticated staff users.

    Used for:
    - Admin APIs (/api/admin/*)
    - Sensitive backend operations
    """

    message = "Admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


# ==================================================
# SUPER ADMIN PERMISSION
# ==================================================
class IsSuperAdmin(BasePermission):
    """
    Allows access only to superusers.

    Use for:
    - Dangerous operations
    - System-level actions
    """

    message = "Super admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )


# ==================================================
# ROLE-BASED PERMISSION (FUTURE-READY)
# ==================================================
class HasAdminRole(BasePermission):
    """
    Role-based admin permission.

    This checks Django Groups.
    Example roles:
    - manager
    - support
    - inventory

    Usage:
        permission_classes = [HasAdminRole]
        required_roles = ["manager", "support"]
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if not (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        ):
            return False

        required_roles = getattr(view, "required_roles", None)

        # If no specific roles required, allow any admin
        if not required_roles:
            return True

        user_roles = set(
            request.user.groups.values_list("name", flat=True)
        )

        return bool(user_roles.intersection(required_roles))


# ==================================================
# READ-ONLY ADMIN PERMISSION
# ==================================================
class IsReadOnlyAdmin(BasePermission):
    """
    Allows read-only access for admin users.

    Useful for:
    - Support staff
    - Analytics viewers
    """

    message = "Read-only admin access."

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        return (
            request.method in self.SAFE_METHODS
            and request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
