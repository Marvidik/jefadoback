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

class SellerRegisterSerializer(RegisterSerializer):
    store_name = serializers.CharField(max_length=255)
    rc_number = serializers.CharField(max_length=50, required=False)
    
    # We remove username field from default registration
    username = None

    @transaction.atomic
    def save(self, request):
        user = super().save(request)
        user.user_type = 'SELLER'
        user.save()
        
        # Create Seller Profile
        SellerProfile.objects.create(
            user=user,
            store_name=self.validated_data.get('store_name'),
            rc_number=self.validated_data.get('rc_number')
        )
        return user

    def validate_store_name(self, value):
        slug = slugify(value)
        if SellerProfile.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value

class CustomLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField(required=True)
