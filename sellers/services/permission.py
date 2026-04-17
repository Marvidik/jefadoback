from rest_framework.permissions import BasePermission


class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, "seller_profile")

    def has_object_permission(self, request, view, obj):
        return obj.seller == request.user.seller_profile