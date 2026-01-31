class LandingAdminMixin:
    """
    Groups landing-related models
    under 'Landing Page' in Django Admin.
    """

    def get_model_perms(self, request):
        perms = super().get_model_perms(request)

        # Override app label for admin grouping ONLY
        self.model._meta.app_label = "Landing Page"

        return perms
