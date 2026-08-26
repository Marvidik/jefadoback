from decimal import Decimal


REFERRAL_REWARD = Decimal("100.00")

# The referred user must successfully fund at least this amount
# before the referral becomes eligible for the reward.
REFERRAL_MINIMUM_FUNDING = Decimal("500.00")

REFERRAL_REWARD_TYPE = "REFERRAL_REWARD"

REFERRAL_CODE_LENGTH = 8
