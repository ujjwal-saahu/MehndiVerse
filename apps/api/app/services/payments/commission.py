"""Platform commission calculation — see
docs/payments.md#8-platform-commission-and-artist-earnings.

Pure function, no I/O — deliberately isolated here so it's trivially unit
testable without a database or a payment provider.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommissionSplit:
    gross_amount: int
    commission_amount: int
    net_amount: int


def calculate_commission(amount_minor: int, commission_percent: float) -> CommissionSplit:
    """`amount_minor` is the gross payment (integer minor units). The
    commission is rounded to the nearest minor unit (banker's-rounding-free
    `round()` on a value that's already an integer times a float percentage
    is fine here — a single paisa of rounding drift is immaterial and any
    reconciliation drift is caught by
    docs/payments.md#10-reconciliation-command, not by chasing sub-unit
    precision here). `commission_amount + net_amount` always equals
    `amount_minor` exactly, by construction (net is computed as the
    remainder, not independently rounded)."""
    if amount_minor <= 0:
        raise ValueError("amount_minor must be positive.")
    if commission_percent < 0 or commission_percent > 100:
        raise ValueError("commission_percent must be between 0 and 100.")

    commission_amount = round(amount_minor * (commission_percent / 100))
    net_amount = amount_minor - commission_amount
    return CommissionSplit(
        gross_amount=amount_minor, commission_amount=commission_amount, net_amount=net_amount
    )
