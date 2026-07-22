"""Selects which `PaymentProvider` implementation the app uses — see
docs/payments.md#1-payment-provider-abstraction. This is the *only* place
that needs to change to add a provider for another region later.
"""

from app.core.config import Settings, get_settings

from .base import PaymentProvider
from .razorpay_provider import RazorpayProvider

# Region -> default provider name. "IN" (India) is the only region this
# project serves today, so Razorpay (India's dominant gateway, with UPI/
# card/netbanking support and a well-documented test mode) is the only
# concrete provider implemented. `settings.payment_provider`, when set,
# overrides the region's default explicitly.
_REGION_DEFAULT_PROVIDER: dict[str, str] = {
    "IN": "razorpay",
}


def get_payment_provider(settings: Settings | None = None) -> PaymentProvider:
    settings = settings or get_settings()
    provider_name = settings.payment_provider or _REGION_DEFAULT_PROVIDER.get(
        settings.payment_region
    )
    if provider_name == "razorpay":
        return RazorpayProvider(settings)
    raise ValueError(
        f"No payment provider configured for region {settings.payment_region!r} "
        f"(payment_provider={settings.payment_provider!r})."
    )
