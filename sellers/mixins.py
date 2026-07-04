# subscriptions/mixins.py

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from transactions.models import UserSubscription
from sellers.models import Product, Service


class SellerPlanRequiredMixin:
    """
    Restricts seller actions based on subscription features.

    Usage:

    class ProductListCreateView(
        SellerPlanRequiredMixin,
        generics.ListCreateAPIView
    ):
        required_feature = "products"
    """

    required_feature = None

    # Slug used for sellers with no active subscription
    DEFAULT_PLAN_SLUG = "basic"

    PLAN_FEATURES = {
        "basic": {
            "products": True,
            "services": True,
            "coupons": False,
            "analytics": False,
            "priority_support": False,
            "custom_store_url": False,
            "bulk_import_export": False,
            "max_products": 10,
            "max_services": 5,
        },

        "pro": {
            "products": True,
            "services": True,
            "coupons": True,
            "analytics": True,
            "priority_support": True,
            "custom_store_url": True,
            "bulk_import_export": True,
            "max_products": None,
            "max_services": None,
        },

        "enterprise": {
            "products": True,
            "services": True,
            "coupons": True,
            "analytics": True,
            "priority_support": True,
            "custom_store_url": True,
            "bulk_import_export": True,
            "api_access": True,
            "white_label": True,
            "max_products": None,
            "max_services": None,
        },
    }

    def get_active_subscription(self):
        return (
            UserSubscription.objects
            .select_related("plan")
            .filter(
                user=self.request.user,
                status=UserSubscription.STATUS_ACTIVE,
                end_date__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

    def get_plan_slug(self):
        """
        Returns the effective plan slug for the current user:
        their active subscription's plan, or "basic" if none exists.
        """
        subscription = self.get_active_subscription()

        if not subscription:
            return self.DEFAULT_PLAN_SLUG

        return subscription.plan.slug

    def get_plan_features(self):
        slug = self.get_plan_slug()
        return self.PLAN_FEATURES.get(slug, self.PLAN_FEATURES[self.DEFAULT_PLAN_SLUG])

    def check_plan_feature(self):
        if not self.required_feature:
            return

        features = self.get_plan_features()

        allowed = features.get(self.required_feature)

        if not allowed:
            raise PermissionDenied(
                "Your current plan does not support this feature."
            )

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.check_plan_feature()


class ProductLimitMixin:
    def check_product_limit(self):
        features = self.get_plan_features()
        max_products = features.get("max_products")
        if max_products is None:
            return
        seller = self.request.user.seller_profile
        if Product.objects.filter(seller=seller).count() >= max_products:
            raise PermissionDenied(f"Your plan only allows {max_products} products.")


class ServiceLimitMixin:

    def check_service_limit(self):

        features = self.get_plan_features()

        max_services = features.get("max_services")

        if max_services is None:
            return

        seller = self.request.user.seller_profile

        current_count = Service.objects.filter(
            seller=seller
        ).count()

        if current_count >= max_services:
            raise PermissionDenied(
                f"Your plan only allows {max_services} services."
            )