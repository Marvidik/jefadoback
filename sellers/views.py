from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from sellers.services.bankservice import BankAccountService
from sellers.services.couponservice import CouponService
from sellers.services.dashboardservices import DashboardService
from sellers.services.orderservices import OrderAnalyticsService
from sellers.services.payoutservice import PayoutService
from sellers.services.profileservice import SellerProfileService
from sellers.services.serviceservices import ServiceService
from transactions.models import Order

from .models import Product
from .serializers import BankAccountSerializer, ChangePasswordSerializer, CouponSerializer, OrderItemSerializer, OrderListSerializer, OrderStatusUpdateSerializer, PayoutRequestSerializer, ProductSerializer, SellerProfileSerializer, ServiceSerializer
from .services.productservices import ProductService
from .filters import OrderFilter, ProductFilter, ServiceFilter
from .services.permission import IsSeller
from .pagination import SellerPagination
from rest_framework.views import APIView
from rest_framework import status

from django.db.models import Sum, Count
from django.utils.timezone import now
from datetime import timedelta
from collections import defaultdict



class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]
    pagination_class = SellerPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-created_at"]

    @extend_schema(summary="List & Create Products")
    def get_queryset(self):
        return ProductService.get_seller_products(
            seller=self.request.user.seller_profile
        )

    def perform_create(self, serializer):
        ProductService.create_product(
            seller=self.request.user.seller_profile,
            data=serializer.validated_data
        )


class ProductRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_object(self):
        return ProductService.get_product(
            seller=self.request.user.seller_profile,
            pk=self.kwargs["pk"]
        )

    @extend_schema(summary="Retrieve Product")
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @extend_schema(summary="Update Product (Full)")
    def put(self, *args, **kwargs):
        return super().put(*args, **kwargs)

    @extend_schema(summary="Partial Update Product")
    def patch(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(summary="Delete Product")
    def delete(self, *args, **kwargs):
        return super().delete(*args, **kwargs)



class ServiceListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]
    pagination_class = SellerPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]

    filterset_class = ServiceFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return ServiceService.get_seller_services(
            seller=self.request.user.seller_profile
        )

    def perform_create(self, serializer):
        ServiceService.create_service(
            seller=self.request.user.seller_profile,
            data=serializer.validated_data
        )


class ServiceRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_object(self):
        return ServiceService.get_service(
            seller=self.request.user.seller_profile,
            pk=self.kwargs["pk"]
        )

    @extend_schema(summary="Retrieve Service")
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @extend_schema(summary="Update Service (Full)")
    def put(self, *args, **kwargs):
        return super().put(*args, **kwargs)

    @extend_schema(summary="Partial Update Service")
    def patch(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(summary="Delete Service")
    def delete(self, *args, **kwargs):
        return super().delete(*args, **kwargs)
    


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get(self, request):

        seller = request.user.seller_profile

        cards = DashboardService.get_summary_cards(seller)
        chart = DashboardService.get_monthly_earnings(seller)

        bestsellers = DashboardService.get_best_selling_products(seller)

        orders = DashboardService.get_recent_orders(seller)

        return Response({
            "cards": cards,
            "chart": chart,
            "bestsellers": [
                {
                    "product": p.name,
                    "price": p.price,
                    "units_sold": p.units_sold,
                    "net_profit": p.net_profit,
                }
                for p in bestsellers
            ],
            "orders": [
                {
                    "id": o.id,
                    "buyer": o.buyer_name,
                    "revenue": o.revenue,
                    "net_profit": o.net_profit,
                    "status": o.status,
                    "created_at": o.created_at,
                }
                for o in orders
            ]
        })



class OrderListPageView(generics.ListAPIView):

    serializer_class = OrderListSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):

        seller = self.request.user.seller_profile

        return Order.objects.filter(
            items__product__seller=seller,status__in=["COMPLETED","PROCESSING","PAID"]
        ).distinct().order_by("-created_at")

class UpdateOrderStatusView(APIView):

    def patch(self, request, order_id):
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderAnalyticsService.update_order_status(
                order_id=order_id,
                new_status=serializer.validated_data["status"],
                seller = request.user.seller_profile 
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Order status updated",
            "order_id": order.id,
            "status": order.status
        })

class OrderAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        seller = request.user.seller_profile

        return Response({
            "cards": OrderAnalyticsService.get_cards(seller),
            "chart": OrderAnalyticsService.get_chart(seller),
        })
    

class ServiceOrderListPageView(generics.ListAPIView):

    serializer_class = OrderListSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):

        seller = self.request.user.seller_profile

        return Order.objects.filter(
            items__service__seller=seller,status__in=["COMPLETED","PROCESSING","PAID"]
        ).distinct().order_by("-created_at")



class CouponListCreateView(generics.ListCreateAPIView):

    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        seller = self.request.user.seller_profile
        return CouponService.list_coupons(seller)

    def perform_create(self, serializer):
        seller = self.request.user.seller_profile
        CouponService.create_coupon(seller, serializer.validated_data)



class CouponUpdateView(APIView):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):

        seller = request.user.seller_profile

        coupon = CouponService.update_coupon(pk, seller, request.data)

        return Response(CouponSerializer(coupon).data)
    

class CouponDeleteView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):

        seller = request.user.seller_profile

        CouponService.delete_coupon(pk, seller)

        return Response({"message": "deleted"})
    



class SellerProfileView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsSeller]
    serializer_class = SellerProfileSerializer

    def get(self, request):

        profile = SellerProfileService.get_profile(request.user)
        return Response(SellerProfileSerializer(profile).data)

    def patch(self, request):

        profile = SellerProfileService.update_profile(
            request.user,
            request.data
        )

        return Response(SellerProfileSerializer(profile).data)
    


class BankAccountListCreateView(generics.ListCreateAPIView):

    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_queryset(self):
        return BankAccountService.list_accounts(
            self.request.user.seller_profile
        )

    def perform_create(self, serializer):
        BankAccountService.create_account(
            self.request.user.seller_profile,
            serializer.validated_data
        )



class BankAccountDeleteView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def delete(self, request, pk):

        BankAccountService.delete_account(
            pk,
            request.user.seller_profile
        )

        return Response({"message": "deleted"})
    
class PayoutCardsView(APIView):
    permission_classes = [permissions.IsAuthenticated,IsSeller]

    def get(self, request):

        seller = request.user.seller_profile

        data = PayoutService.get_cards(seller)

        return Response({
            "status": "success",
            "data": data
        })

class PayoutRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = PayoutRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsSeller]

    def get_queryset(self):
        return PayoutService.list_requests(
            self.request.user.seller_profile
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Call your original service exactly as it is
            payout_obj = PayoutService.create_request(
                self.request.user.seller_profile,
                serializer.validated_data
            )
            
            # Standard success response
            headers = self.get_success_headers(serializer.data)
            return Response(
                PayoutRequestSerializer(payout_obj).data, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
            
        except ValueError as e:
            # Catches your "Insufficient balance" or "Invalid amount" raises
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Catches any other unexpected issues (like bank account not found)
            # and returns them neatly instead of a 500 omo crash.
            return Response(
                {"error": "An error occurred while processing your request.", "details": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )



class ChangePasswordView(generics.GenericAPIView):
    """
    An endpoint for changing password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        serializer.is_valid(raise_exception=True)
        
        # Update the password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response(
            {"detail": "Password updated successfully."}, 
            status=status.HTTP_200_OK
        )