from rest_framework import serializers

from .constants import (
    REFERRAL_MINIMUM_FUNDING,
    REFERRAL_REWARD,
)
from .models import Referral, ReferralCode


class ReferralCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralCode
        fields = [
            "code",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "code",
            "is_active",
            "created_at",
        ]


class ClaimReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(
        max_length=20,
        trim_whitespace=True,
    )

    def validate_referral_code(self, value):
        value = value.strip().upper()

        if not value:
            raise serializers.ValidationError(
                "Referral code is required."
            )

        return value


class ReferralSerializer(serializers.ModelSerializer):
    referrer_email = serializers.EmailField(
        source="referrer.email",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Referral
        fields = [
            "id",
            "referrer_email",
            "status",
            "status_display",
            "created_at",
            "qualified_at",
            "rewarded_at",
        ]
        read_only_fields = fields


class ReferralStatsSerializer(serializers.Serializer):
    code = serializers.CharField()
    total_referrals = serializers.IntegerField()
    successful_referrals = serializers.IntegerField()
    pending_referrals = serializers.IntegerField()
    total_earned = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    reward_per_referral = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    minimum_funding = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


class ReferralRewardSerializer(serializers.Serializer):
    rewarded = serializers.BooleanField()
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    message = serializers.CharField()
