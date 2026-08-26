from django.db import IntegrityError
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .constants import REFERRAL_REWARD
from .models import Referral
from .serializers import (
    ClaimReferralSerializer,
    ReferralCodeSerializer,
    ReferralSerializer,
    ReferralStatsSerializer,
)
from .services import ReferralService


class MyReferralCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={
            200: ReferralCodeSerializer,
        }
    )
    def get(self, request):
        referral_code = ReferralService.get_or_create_code(
            request.user
        )

        return Response(
            ReferralCodeSerializer(referral_code).data
        )


class ClaimReferralView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ClaimReferralSerializer,
        responses={
            201: ReferralSerializer,
            400: OpenApiResponse(
                description="Invalid referral code or account already has a referral.",
            ),
        },
    )
    def post(self, request):
        serializer = ClaimReferralSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            referral = ReferralService.create_referral(
                user=request.user,
                code=serializer.validated_data["referral_code"],
                request=request,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "This account already has a referral."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ReferralSerializer(referral).data,
            status=status.HTTP_201_CREATED,
        )


class MyReferralStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={
            200: ReferralStatsSerializer,
        }
    )
    def get(self, request):
        stats = ReferralService.get_referral_stats(
            request.user
        )

        serializer = ReferralStatsSerializer(stats)

        return Response(serializer.data)


class MyReferralListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReferralSerializer

    def get_queryset(self):
        return (
            Referral.objects
            .select_related(
                "referrer",
                "referred_user",
            )
            .filter(
                referrer=self.request.user,
            )
            .order_by("-created_at")
        )


class MyReferrerView(APIView):
    """
    Returns the person who referred the logged-in user.
    Returns null if the user was not referred by anyone.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={
            200: ReferralSerializer,          # or a smaller serializer if you prefer
            204: OpenApiResponse(description="No referrer found"),
        }
    )
    def get(self, request):
        try:
            referral = (
                Referral.objects
                .select_related("referrer")
                .get(referred_user=request.user)
            )
        except Referral.DoesNotExist:
            return Response(
                {"referrer": None},
                status=status.HTTP_200_OK,
            )

        return Response(
            ReferralSerializer(referral).data,
            status=status.HTTP_200_OK,
        )