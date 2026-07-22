"""Payment-provider abstraction — see docs/payments.md#1-payment-provider-
abstraction.

Every concrete provider (Razorpay today, for the "IN" region — see
`razorpay_provider.py`) implements this same interface. Callers
(`app/services/payments/service.py`) depend only on this module and
`factory.py`'s `get_payment_provider()` — never on a concrete provider
module directly — so adding a provider for another region later never
requires changing service/route code, only the factory's selection (and the
new provider module itself).

All amounts everywhere in this interface are integer **minor currency
units** (e.g. paise, not rupees) — see
docs/payments.md#7-integer-minor-currency-units. No concrete provider
implementation may accept or return a float/Decimal amount.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderOrder:
    """What a client needs to actually launch the provider's checkout —
    `provider_key_id` is a *publishable* identifier (safe to send to a
    browser/app; it is not a secret), never the provider's API secret."""

    provider_order_id: str
    amount_minor: int
    currency: str
    provider_key_id: str


@dataclass(frozen=True)
class ProviderWebhookEvent:
    """A normalized webhook event — every provider's raw payload shape gets
    translated into this before any service-layer code touches it, so
    `service.py` never needs to know Razorpay's (or any other provider's)
    specific JSON shape."""

    event_type: str
    provider_order_id: str | None
    provider_payment_id: str | None
    provider_refund_id: str | None
    amount_minor: int | None
    currency: str | None
    status: str
    failure_reason: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class ProviderPaymentStatus:
    """The result of asking the provider directly "what happened to this
    payment" (used by reconciliation — see
    docs/payments.md#10-reconciliation-command — and as a fallback the
    webhook path doesn't depend on)."""

    provider_payment_id: str | None
    status: str
    amount_minor: int | None
    currency: str | None
    failure_reason: str | None


@dataclass(frozen=True)
class ProviderRefund:
    provider_refund_id: str
    status: str
    amount_minor: int


class PaymentProvider(ABC):
    @abstractmethod
    def create_order(
        self, *, amount_minor: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder: ...

    @abstractmethod
    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        """Must use a constant-time comparison — see
        docs/payments.md#5-signed-webhook-handling-and-duplicate-protection."""
        ...

    @abstractmethod
    def parse_webhook_event(self, *, raw_body: bytes) -> ProviderWebhookEvent:
        """Only ever called after `verify_webhook_signature` has returned
        True — parsing an unverified payload is never safe to act on."""
        ...

    @abstractmethod
    def get_order_status(self, *, provider_order_id: str) -> ProviderPaymentStatus:
        """Confirms payment status directly against the provider's API —
        the "or provider API" half of "confirm payment through a verified
        webhook or provider API." Used by reconciliation, never trusted from
        client input."""
        ...

    @abstractmethod
    def create_refund(self, *, provider_payment_id: str, amount_minor: int) -> ProviderRefund: ...
