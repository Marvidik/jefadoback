from django.contrib import admin
from .models import SellerProfile, Category, Product
@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'is_verified', 'verification_status', 'created_at')
    list_filter = ('is_verified', 'verification_status')
    search_fields = ('store_name', 'user__email')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'category', 'price', 'stock_qty', 'status')
    list_filter = ('status', 'category')
    search_fields = ('name', 'seller__store_name')

