"""Razorpay sandbox/test-mode integration — the `PaymentProvider` this
project uses for its configured "IN" (India) region. See
docs/payments.md#2-sandbox-integration-razorpay.

Mirrors app/integrations/supabase_storage.py's pattern: a small, mockable
httpx wrapper rather than the Razorpay Python SDK, so the HTTP boundary
stays trivial to test (respx, already a dev dependency) and the only place
holding `razorpay_key_secret` is this module. Razorpay's *test-mode* API is
just their normal API hit with test-mode keys (`rzp_test_...`) — there is no
separate sandbox host, so nothing here is reachable without real (if
placeholder-default) credentials, and secrets always come from
`app.core.config.Settings`, never hardcoded.
"""

import hashlib
import hmac
import json

import httpx

from app.core.config import Settings
from app.core.resilience import razorpay_breaker, retry_connect_only, retry_idempotent

from .base import (
    PaymentProvider,
    ProviderOrder,
    ProviderPaymentStatus,
    ProviderRefund,
    ProviderWebhookEvent,
)


class RazorpayError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class RazorpayProvider(PaymentProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._settings.razorpay_api_base_url,
            auth=(self._settings.razorpay_key_id, self._settings.razorpay_key_secret),
            timeout=15.0,
        )

    def _raise_for_error(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
            message = (body.get("error") or {}).get("description") or str(body)
        except ValueError:
            message = response.text
        raise RazorpayError(response.status_code, message)

    def create_order(
        self, *, amount_minor: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder:
        with self._client() as client:
            response = razorpay_breaker.call(
                lambda: retry_connect_only(
                    lambda: client.post(
                        "/orders",
                        json={
                            "amount": amount_minor,
                            "currency": currency,
                            "receipt": receipt,
                            "notes": notes,
                        },
                    )
                )
            )
        self._raise_for_error(response)
        body = response.json()
        return ProviderOrder(
            provider_order_id=body["id"],
            amount_minor=body["amount"],
            currency=body["currency"],
            provider_key_id=self._settings.razorpay_key_id,
        )

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        expected = hmac.new(
            self._settings.razorpay_webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        # constant-time comparison — see docs/payments.md#5.
        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(self, *, raw_body: bytes) -> ProviderWebhookEvent:
        body = json.loads(raw_body)
        event_type = body["event"]
        payload = body.get("payload", {})

        if "refund" in payload:
            entity = payload["refund"]["entity"]
            return ProviderWebhookEvent(
                event_type=event_type,
                provider_order_id=None,
                provider_payment_id=entity.get("payment_id"),
                provider_refund_id=entity["id"],
                amount_minor=entity.get("amount"),
                currency=entity.get("currency"),
                status=entity.get("status", event_type),
                failure_reason=None,
                raw=body,
            )

        entity = payload["payment"]["entity"]
        return ProviderWebhookEvent(
            event_type=event_type,
            provider_order_id=entity.get("order_id"),
            provider_payment_id=entity.get("id"),
            provider_refund_id=None,
            amount_minor=entity.get("amount"),
            currency=entity.get("currency"),
            status=entity.get("status", event_type),
            failure_reason=entity.get("error_description"),
            raw=body,
        )

    def get_order_status(self, *, provider_order_id: str) -> ProviderPaymentStatus:
        with self._client() as client:
            response = razorpay_breaker.call(
                lambda: retry_idempotent(
                    lambda: client.get(f"/orders/{provider_order_id}/payments")
                )
            )
        self._raise_for_error(response)
        items = response.json().get("items", [])
        if not items:
            return ProviderPaymentStatus(
                provider_payment_id=None,
                status="created",
                amount_minor=None,
                currency=None,
                failure_reason=None,
            )
        # An order can accumulate multiple payment attempts (e.g. a failed
        # card retry) — the most recent attempt is authoritative.
        latest = items[-1]
        return ProviderPaymentStatus(
            provider_payment_id=latest["id"],
            status=latest["status"],
            amount_minor=latest["amount"],
            currency=latest["currency"],
            failure_reason=latest.get("error_description"),
        )

    def create_refund(self, *, provider_payment_id: str, amount_minor: int) -> ProviderRefund:
        with self._client() as client:
            response = razorpay_breaker.call(
                lambda: retry_connect_only(
                    lambda: client.post(
                        f"/payments/{provider_payment_id}/refund",
                        json={"amount": amount_minor},
                    )
                )
            )
        self._raise_for_error(response)
        body = response.json()
        return ProviderRefund(
            provider_refund_id=body["id"], status=body["status"], amount_minor=body["amount"]
        )
