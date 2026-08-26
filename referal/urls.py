from django.urls import path

from .views import (
    ClaimReferralView,
    MyReferralCodeView,
    MyReferralListView,
    MyReferralStatsView,
)


urlpatterns = [
    path(
        "me/code/",
        MyReferralCodeView.as_view(),
        name="my-referral-code",
    ),
    path(
        "claim/",
        ClaimReferralView.as_view(),
        name="claim-referral",
    ),
    path(
        "me/stats/",
        MyReferralStatsView.as_view(),
        name="my-referral-stats",
    ),
    path(
        "me/referrals/",
        MyReferralListView.as_view(),
        name="my-referral-list",
    ),
]
