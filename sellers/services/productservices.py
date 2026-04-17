from django.shortcuts import get_object_or_404
from ..models import Product


class ProductService:

    @staticmethod
    def create_product(*, seller, data):
        return Product.objects.create(seller=seller, **data)

    @staticmethod
    def update_product(*, product, data):
        for attr, value in data.items():
            setattr(product, attr, value)
        product.save()
        return product

    @staticmethod
    def delete_product(*, product):
        product.delete()

    @staticmethod
    def get_seller_products(*, seller):
        return Product.objects.filter(seller=seller)

    @staticmethod
    def get_product(*, seller, pk):
        return get_object_or_404(Product, pk=pk, seller=seller)