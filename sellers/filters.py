import django_filters

from transactions.models import Order
from .models import Product, Service
from django.utils.timezone import now
from datetime import timedelta


class ProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category__id")

    # 👇 make status case-insensitive
    status = django_filters.CharFilter(
        field_name="status",
        lookup_expr="iexact"
    )

    class Meta:
        model = Product
        fields = ["category", "status"]



class ServiceFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category__id")

    status = django_filters.CharFilter(
        field_name="status",
        lookup_expr="iexact"
    )

    class Meta:
        model = Service
        fields = ["category", "status"]




class OrderFilter(django_filters.FilterSet):

    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    search = django_filters.CharFilter(method="filter_search")
    period = django_filters.CharFilter(method="filter_period")

    class Meta:
        model = Order
        fields = ["status"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            buyer_name__icontains=value
        ) | queryset.filter(
            buyer_email__icontains=value
        )

    def filter_period(self, queryset, name, value):
        today = now()

        if value == "today":
            return queryset.filter(created_at__date=today.date())

        if value == "week":
            return queryset.filter(created_at__gte=today - timedelta(days=7))

        if value == "month":
            return queryset.filter(created_at__gte=today - timedelta(days=30))

        return queryset