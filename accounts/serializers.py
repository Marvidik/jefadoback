from rest_framework import serializers

from transactions.models import Order, OrderItem
from .models import User
from sellers.models import SellerProfile
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.db import transaction
from django.utils.text import slugify
from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, Address, Wishlist

from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'user_type', 'phone', 'first_name', 'last_name')
        read_only_fields = ('id', 'email', 'user_type')



class CustomLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField(required=True)


class CustomRegisterSerializer(RegisterSerializer):
    # Extra fields
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    store_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    rc_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    # We still hide username if you don't want it
    username = None

    def validate(self, data):
        # If user wants to register as seller, store_name is required
        user_type = data.get('user_type')
        if user_type == 'SELLER' and not data.get('store_name'):
            raise serializers.ValidationError({"store_name": "Store name is required for sellers."})
        return data

    @transaction.atomic
    def save(self, request):
        # Get user_type from request data (default to BUYER)
        user_type = self.validated_data.get('user_type', 'BUYER')

        # Create the User
        user = super().save(request)
        
        # Set user type
        user.user_type = user_type
        user.first_name = self.validated_data.get('first_name', '')
        user.last_name = self.validated_data.get('last_name', '')
        user.save()

        # Only create SellerProfile if registering as SELLER
        if user_type == 'SELLER':
            store_name = self.validated_data.get('store_name')
            rc_number = self.validated_data.get('rc_number')

            SellerProfile.objects.create(
                user=user,
                store_name=store_name,
                rc_number=rc_number,
                # You can add more fields later (description, logo, etc.)
            )

        return user

    def validate_store_name(self, value):
        if not value:
            return value
        slug = slugify(value)
        if SellerProfile.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value






class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone = serializers.CharField(source='user.phone', required=False)
    total_orders = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'gender',
            'date_of_birth', 'bio',
            'notify_order_updates', 'notify_promotions', 'notify_new_arrivals',
            'notify_price_drops', 'notify_review_reminders', 'notify_newsletter',
            'notify_sms', 'notify_push',
            'total_orders'
        ]

    def get_total_orders(self, obj):
        return obj.user.orders.count()

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {}) if 'user' in validated_data else {}
        
        # Update User fields
        user = instance.user
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)
        user.phone = user_data.get('phone', user.phone)
        user.save()

        # Update Profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'label', 'full_name', 'street_address', 'city', 'state',
                  'country', 'postal_code', 'phone', 'is_default']

class WishlistAddSerializer(serializers.Serializer):
    """Simple serializer for adding to wishlist"""
    product = serializers.IntegerField(help_text="Product ID to add to wishlist")

class WishlistSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()   # or use a minimal Product serializer

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'created_at']

    def get_product(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'slug': obj.product.slug,
            'price': obj.product.price,
            'image': obj.product.image
        }



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        
        # Check if old password is correct
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({"old_password": "Wrong old password."})
            
        return attrs



class OrderItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    item_type = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'name', 'image', 'item_type', 'quantity', 'price']

    def get_name(self, obj):
        if obj.product:
            return obj.product.name
        elif obj.service:
            return obj.service.name
        return "Unknown Item"

    def get_image(self, obj):
        if obj.product and obj.product.image:
            return obj.product.image
        elif obj.service and obj.service.image:
            return obj.service.image
        return None

    def get_item_type(self, obj):
        return "product" if obj.product else "service"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_date = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'buyer_name', 'buyer_email', 'buyer_phone',
            'order_type', 'total_amount', 'status', 'status_display',
            'order_date', 'address', 'city', 'state', 'country',
            'items'
        ]



class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField()



class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()