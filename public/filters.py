import django_filters
from  sellers.models import Product, Service

class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    min_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='gte'
    )

    # optional: max rating
    max_rating = django_filters.NumberFilter(
        field_name='rating',
        lookup_expr='lte'
    )

    price_range = django_filters.CharFilter(method='filter_queryset')

    class Meta:
        model = Product
        fields = ['category', 'min_rating', 'max_rating']

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        price_range = self.request.GET.get('price_range')
        if price_range:
            if price_range == 'under_100':
                queryset = queryset.filter(price__lt=100)
            elif price_range == '100_500':
                queryset = queryset.filter(price__gte=100, price__lte=500)
            elif price_range == '500_1000':
                queryset = queryset.filter(price__gte=500, price__lte=1000)
            elif price_range == 'over_1000':
                queryset = queryset.filter(price__gt=1000)
        return queryset


class ServiceFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Service
        fields = ['category']