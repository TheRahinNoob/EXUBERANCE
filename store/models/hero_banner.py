from django.db import models
from django.utils.timezone import now


class HeroBanner(models.Model):
    image_desktop = models.ImageField(
        upload_to="banners/desktop/",
        help_text="Large screens (≥1024px)",
    )
    image_tablet = models.ImageField(
        upload_to="banners/tablet/",
        help_text="Tablets & small laptops",
    )
    image_mobile = models.ImageField(
        upload_to="banners/mobile/",
        help_text="Mobile screens",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Disable to hide banner without deleting",
    )
    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional visibility start time",
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional visibility end time",
    )
    ordering = models.PositiveIntegerField(
        default=0,
        help_text="Lower number = higher priority",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Used for stable ordering & auditing",
    )

    class Meta:
        ordering = ("ordering", "-created_at")
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["starts_at"]),
            models.Index(fields=["ends_at"]),
            models.Index(fields=["created_at"]),
        ]

    @property
    def is_live(self) -> bool:
        if not self.is_active:
            return False

        current = now()
        if self.starts_at and current < self.starts_at:
            return False
        if self.ends_at and current > self.ends_at:
            return False

        return True

    def __str__(self):
        return f"Hero Banner #{self.pk}"
