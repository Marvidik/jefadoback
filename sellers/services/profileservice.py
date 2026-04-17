from django.shortcuts import get_object_or_404
from sellers.models import SellerProfile


class SellerProfileService:

    @staticmethod
    def get_profile(user):
        return get_object_or_404(SellerProfile, user=user)

    @staticmethod
    def update_profile(user, data):
        profile = get_object_or_404(SellerProfile, user=user)

        for key, value in data.items():
            setattr(profile, key, value)

        profile.save()
        return profile