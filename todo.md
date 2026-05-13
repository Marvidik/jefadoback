class ProductListCreateView(
    SellerPlanRequiredMixin,
    ProductLimitMixin,
    generics.ListCreateAPIView
):

    required_feature = "products"

    serializer_class = ProductSerializer

    permission_classes = [
        permissions.IsAuthenticated,
        IsSeller
    ]

    pagination_class = SellerPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]

    filterset_class = ProductFilter

    search_fields = [
        "name",
        "description"
    ]

    ordering_fields = [
        "price",
        "created_at",
        "name"
    ]

    ordering = ["-created_at"]

    def get_queryset(self):

        return ProductService.get_seller_products(
            seller=self.request.user.seller_profile
        )

    def perform_create(self, serializer):

        ProductService.create_product(
            seller=self.request.user.seller_profile,
            data=serializer.validated_data
        )