from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from store.models.landing import (
    HotCategoryBlock,
    HotCategoryBlockItem,
)


# ==================================================
# 🔒 INLINE FORMSET (DUPLICATION PROTECTION)
# ==================================================
class HotCategoryBlockItemInlineFormSet(BaseInlineFormSet):
    """
    Prevent duplicate HotCategory entries
    inside the SAME HotCategoryBlock.
    """

    def clean(self):
        super().clean()

        seen = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            hot_category = form.cleaned_data.get("hot_category")

            if not hot_category:
                continue

            if hot_category in seen:
                raise ValidationError(
                    "❌ You added the same Hot Category more than once "
                    "in this block. Each Hot Category can appear only once."
                )

            seen.add(hot_category)


# ==================================================
# INLINE: HOT CATEGORY BLOCK ITEM
# ==================================================
class HotCategoryBlockItemInline(admin.TabularInline):
    model = HotCategoryBlockItem
    formset = HotCategoryBlockItemInlineFormSet

    extra = 1
    autocomplete_fields = ("hot_category",)
    ordering = ("ordering",)

    fields = (
        "hot_category",
        "ordering",
        "is_active",
    )

    show_change_link = True


# ==================================================
# HOT CATEGORY BLOCK ADMIN
# ==================================================
@admin.register(HotCategoryBlock)
class HotCategoryBlockAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "is_active",
        "ordering",
        "created_at",
    )

    list_editable = (
        "is_active",
        "ordering",
    )

    ordering = ("ordering", "id")
    search_fields = ("title",)

    inlines = (HotCategoryBlockItemInline,)

    fieldsets = (
        (
            "Block Info",
            {
                "fields": ("title",),
            },
        ),
        (
            "Visibility & Order",
            {
                "fields": ("is_active", "ordering"),
            },
        ),
        (
            "System",
            {
                "fields": ("created_at",),
            },
        ),
    )

    readonly_fields = ("created_at",)
