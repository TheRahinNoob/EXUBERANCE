from django.db import models
from django.core.exceptions import ValidationError
from store.models.category import Category


# ==================================================
# ABSTRACT BASE (LANDING SHARED BEHAVIOR)
# ==================================================
class LandingBase(models.Model):
    """
    Abstract base for ALL landing-page-only entities.
    """

    is_active = models.BooleanField(
        default=True,
        help_text="Toggle visibility without deleting the item.",
    )

    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Lower number appears first.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    class Meta:
        abstract = True
        ordering = ("ordering", "id")
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["ordering"]),
        ]


# ==================================================
# LANDING PAGE BODY MENU ITEM
# ==================================================
class LandingMenuItem(LandingBase):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="landing_menu_items",
    )

    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.CharField(max_length=255, blank=True)

    class Meta(LandingBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                name="unique_category_in_landing_menu",
            )
        ]

    def __str__(self):
        return f"{self.category.name} (Landing Menu)"

    @property
    def effective_seo_title(self):
        return self.seo_title or self.category.name

    @property
    def effective_seo_description(self):
        return (
            self.seo_description
            or f"Shop {self.category.name} products at Fabrilife."
        )


# ==================================================
# FEATURED CATEGORY
# ==================================================
class FeaturedCategory(LandingBase):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="featured_categories",
    )

    image = models.ImageField(upload_to="featured-categories/")

    class Meta(LandingBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                name="unique_featured_category",
            )
        ]

    def __str__(self):
        return f"Featured: {self.category.name}"


# ==================================================
# HOT CATEGORY (ATOMIC CONTENT)
# ==================================================
class HotCategory(LandingBase):
    """
    Atomic Hot Category content.
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="hot_categories",
    )

    image = models.ImageField(upload_to="hot-categories/")

    class Meta(LandingBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                name="unique_hot_category",
            )
        ]

    def __str__(self):
        return f"Hot: {self.category.name}"


# ==================================================
# 🔥 HOT CATEGORY BLOCK (COLLECTIVE CONTAINER)
# ==================================================
class HotCategoryBlock(LandingBase):
    """
    ONE collective hot categories section on landing page.
    """

    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Internal CMS title (optional).",
    )

    class Meta(LandingBase.Meta):
        verbose_name = "Hot Category Block"
        verbose_name_plural = "Hot Category Blocks"

    def __str__(self):
        return self.title or f"Hot Category Block #{self.pk}"


# ==================================================
# 🔥 HOT CATEGORY BLOCK ITEM (JOIN TABLE)
# ==================================================
class HotCategoryBlockItem(models.Model):
    """
    ONE HotCategory inside ONE HotCategoryBlock.
    """

    block = models.ForeignKey(
        HotCategoryBlock,
        on_delete=models.CASCADE,
        related_name="items",
    )

    hot_category = models.ForeignKey(
        HotCategory,
        on_delete=models.CASCADE,
        related_name="block_items",
    )

    ordering = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("ordering", "id")
        verbose_name = "Hot Category Block Item"
        verbose_name_plural = "Hot Category Block Items"
        constraints = [
            models.UniqueConstraint(
                fields=["block", "hot_category"],
                name="unique_hot_category_per_block",
            )
        ]

    def __str__(self):
        return f"{self.hot_category} in {self.block}"

    # --------------------------------------------------
    # 🔒 HARD DUPLICATION GUARD (MODEL LEVEL)
    # --------------------------------------------------
    def clean(self):
        """
        Prevent the same HotCategory being added
        twice to the same HotCategoryBlock.
        """

        if HotCategoryBlockItem.objects.filter(
            block=self.block,
            hot_category=self.hot_category,
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                "This Hot Category is already added to this block."
            )
