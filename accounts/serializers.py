from rest_framework import serializers
from .models import User
from sellers.models import SellerProfile
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.db import transaction
from django.utils.text import slugify
from dj_rest_auth.serializers import LoginSerializer

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