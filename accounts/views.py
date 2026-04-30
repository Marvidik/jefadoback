# views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import check_password

from accounts.services import AuthService
from public.pagination import PublicPagination
from transactions.models import Order
from .models import PasswordResetOTP, UserProfile, Address, Wishlist
from .serializers import ChangePasswordSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer, UserProfileSerializer, AddressSerializer, WishlistAddSerializer, WishlistSerializer,OrderSerializer
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema

from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model

User = get_user_model()


@extend_schema(
    request=PasswordResetRequestSerializer,
    responses={200: {"message": "OTP sent"}}
)
class RequestPasswordResetOTPView(APIView):

    def post(self, request):
        email = request.data.get("email")

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"message": "If email exists, OTP sent"})

        otp = AuthService.create_password_reset_otp(user)

        return Response({"message": "OTP sent"})


@extend_schema(
    request=PasswordResetConfirmSerializer,
    responses={200: {"message": "Password reset successful"}}
)
class ConfirmPasswordResetOTPView(APIView):

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "Invalid user"}, status=400)

        record = PasswordResetOTP.objects.filter(
            user=user,
            otp=otp,
            is_used=False
        ).first()

        if not record:
            return Response({"error": "Invalid OTP"}, status=400)

        user.set_password(new_password)
        user.save()

        record.is_used = True
        record.save()

        return Response({"message": "Password reset successful"})

# Profile Get & Update
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Auto-create profile if it doesn't exist
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


# Addresses
class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class SetDefaultAddressView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            address = Address.objects.get(id=pk, user=request.user)
            address.is_default = True
            address.save()
            return Response({"detail": "Address set as default successfully."})
        except Address.DoesNotExist:
            return Response({"detail": "Address not found."}, status=404)


# Wishlist
class WishlistListView(generics.ListAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)


class WishlistAddView(generics.CreateAPIView):
    serializer_class = WishlistAddSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product']

        try:
            product = Product.objects.get(id=product_id)
        except Exception:
            return Response({
                "detail": "Product not found.",
                "message": f"No product with ID {product_id} exists."
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if already in wishlist
        if Wishlist.objects.filter(user=request.user, product_id=product_id).exists():
            return Response({"detail": "Product is already in your wishlist."}, status=status.HTTP_400_BAD_REQUEST)

        

        # Create wishlist item
        wishlist_item = Wishlist.objects.create(
            user=request.user,
            product_id=product_id
        )

        # Return the full item with product details
        result_serializer = WishlistSerializer(wishlist_item)
        return Response({
            "detail": "Product added to wishlist successfully.",
            "item": result_serializer.data
        }, status=status.HTTP_201_CREATED)


class WishlistRemoveView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'product_id'   # We delete by product_id

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def delete(self, request, product_id, *args, **kwargs):
        try:
            wishlist_item = Wishlist.objects.get(user=request.user, product_id=product_id)
            wishlist_item.delete()
            return Response({"detail": "Product removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)
        except Wishlist.DoesNotExist:
            return Response({"detail": "Product not found in your wishlist."}, status=status.HTTP_404_NOT_FOUND)
        

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



class UserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PublicPagination

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']          
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']            

    def get_queryset(self):
        return Order.objects.filter(
            buyer=self.request.user
        ).prefetch_related('items').select_related('buyer')