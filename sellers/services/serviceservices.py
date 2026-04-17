from django.shortcuts import get_object_or_404
from ..models import Service


class ServiceService:

    @staticmethod
    def create_service(*, seller, data):
        return Service.objects.create(seller=seller, **data)

    @staticmethod
    def update_service(*, service, data):
        for attr, value in data.items():
            setattr(service, attr, value)
        service.save()
        return service

    @staticmethod
    def delete_service(*, service):
        service.delete()

    @staticmethod
    def get_seller_services(*, seller):
        return Service.objects.filter(seller=seller)

    @staticmethod
    def get_service(*, seller, pk):
        return get_object_or_404(Service, pk=pk, seller=seller)