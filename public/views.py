# views.py
from rest_framework import generics, filters, permissions, serializers
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from public.pagination import PublicPagination
from sellers.models import Category, Product, SellerProfile, Service
from  .serializers import CategorySerializer, ProductDetailSerializer, ProductSerializer, ReviewSerializer, ServiceDetailSerializer, ServiceSerializer, ShopDetailSerializer, ShopProductSerializer, ShopServiceSerializer
from .filters import ProductFilter, ServiceFilter



class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # Optional: filter by parent slug if needed later



class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(status='PUBLISHED')
    serializer_class = ServiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ServiceFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'rating']
    ordering = ['-created_at']  # default
    pagination_class = PublicPagination


class AlmostSoldOutProductsView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(
            status='PUBLISHED',
            stock_qty__gte=1,
            stock_qty__lte=20
        ).order_by('stock_qty')[:10]  



class FeaturedProductsView(generics.GenericAPIView):
    serializer_class = ProductSerializer

    def get(self, request, *args, **kwargs):
        published = Product.objects.filter(status='PUBLISHED')

        data = {
            "new_arrivals": published.order_by('-created_at')[:10],
            "flash_sale": published.order_by('-stock_sold')[:10],  
            "top_rated": published.order_by('-rating', '-review_count')[:10],
            "best_sellers": published.order_by('-stock_sold')[:10],
        }

        # Serialize each group
        result = {}
        for key, qs in data.items():
            serializer = self.get_serializer(qs, many=True)
            result[key] = serializer.data

        return Response(result)



class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(status='PUBLISHED')
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'rating', 'stock_sold', '-stock_sold']  # most popular via stock_sold
    ordering = ['-created_at']  
    pagination_class = PublicPagination



class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(status='PUBLISHED').select_related('seller', 'category')
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'          # You can change to 'id' if you prefer numeric IDs


class ServiceDetailView(generics.RetrieveAPIView):
    queryset = Service.objects.filter(status='PUBLISHED').select_related('seller', 'category')
    serializer_class = ServiceDetailSerializer
    lookup_field = 'slug'



class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        service_id = self.request.data.get('service')

        if product_id:
            product = Product.objects.get(id=product_id)
            review = serializer.save(user=self.request.user, product=product)
            product.update_rating()
        elif service_id:
            service = Service.objects.get(id=service_id)
            review = serializer.save(user=self.request.user, service=service)
            service.update_rating()
        else:
            raise serializers.ValidationError({"detail": "Provide either 'product' or 'service' id."})

        return review


class ShopDetailView(generics.RetrieveAPIView):
    queryset = SellerProfile.objects.all()
    serializer_class = ShopDetailSerializer
    lookup_field = 'slug'



class ShopListingsView(generics.GenericAPIView):
    pagination_class = PublicPagination

    def get(self, request, slug, *args, **kwargs):
        try:
            seller = SellerProfile.objects.get(slug=slug)
        except SellerProfile.DoesNotExist:
            return Response({"detail": "Shop not found"}, status=404)

        # Base querysets (only published items)
        products = Product.objects.filter(seller=seller, status='PUBLISHED')
        services = Service.objects.filter(seller=seller, status='PUBLISHED')

        
        paginator = self.pagination_class()

        # 1. All Products
        products_page = paginator.paginate_queryset(products.order_by('-created_at'), request)
        products_data = ShopProductSerializer(products_page, many=True).data

        # 2. All Services
        services_page = paginator.paginate_queryset(services.order_by('-created_at'), request)
        services_data = ShopServiceSerializer(services_page, many=True).data

        # 3. Best Sellers (by stock_sold)
        best_sellers_qs = products.order_by('-stock_sold')[:10]
        best_sellers_data = ShopProductSerializer(best_sellers_qs, many=True).data

        # 4. New Arrivals (latest 10 products)
        new_arrivals_qs = products.order_by('-created_at')[:10]
        new_arrivals_data = ShopProductSerializer(new_arrivals_qs, many=True).data

        return Response({
            "shop": ShopDetailSerializer(seller).data,
            "products": {
                "count": products.count(),
                "results": products_data,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            },
            "services": {
                "count": services.count(),
                "results": services_data,
                "next": paginator.get_next_link(),      # You can improve this later
                "previous": paginator.get_previous_link(),
            },
            "best_sellers": best_sellers_data,          # Top 10, not paginated
            "new_arrivals": new_arrivals_data           # Latest 10, not paginated
        })