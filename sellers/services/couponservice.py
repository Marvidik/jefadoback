from django.shortcuts import get_object_or_404
from transactions.models import Coupon
from ..models import Product
from  ..models import Service


class CouponService:

    @staticmethod
    def list_coupons(seller):
        return Coupon.objects.filter(seller=seller).prefetch_related(
        )

    @staticmethod
    def create_coupon(seller, data):

       

        coupon = Coupon.objects.create(seller=seller, **data)

        return coupon

    @staticmethod
    def update_coupon(coupon_id, seller, data):

        coupon = get_object_or_404(Coupon, id=coupon_id, seller=seller)

        for key, value in data.items():
            setattr(coupon, key, value)

        coupon.save()
        return coupon
    @staticmethod
    def delete_coupon(coupon_id, seller):
        coupon = get_object_or_404(Coupon, id=coupon_id, seller=seller)
        coupon.delete()
        return True