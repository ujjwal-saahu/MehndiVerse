"""Platform commission calculation — see
docs/payments.md#8-platform-commission-and-artist-earnings."""

import pytest

from app.services.payments.commission import calculate_commission


def test_commission_split_sums_to_the_gross_amount() -> None:
    split = calculate_commission(50000, 15.0)
    assert split.gross_amount == 50000
    assert split.commission_amount + split.net_amount == 50000


def test_commission_is_fifteen_percent_of_gross() -> None:
    split = calculate_commission(100000, 15.0)
    assert split.commission_amount == 15000
    assert split.net_amount == 85000


def test_zero_percent_commission_gives_all_to_the_artist() -> None:
    split = calculate_commission(50000, 0.0)
    assert split.commission_amount == 0
    assert split.net_amount == 50000


def test_hundred_percent_commission_gives_nothing_to_the_artist() -> None:
    split = calculate_commission(50000, 100.0)
    assert split.commission_amount == 50000
    assert split.net_amount == 0


def test_commission_rounds_to_the_nearest_minor_unit() -> None:
    # 33333 * 0.15 = 4999.95 -> rounds to 5000, net is the exact remainder.
    split = calculate_commission(33333, 15.0)
    assert split.commission_amount == 5000
    assert split.net_amount == 28333
    assert split.commission_amount + split.net_amount == 33333


def test_rejects_non_positive_amount() -> None:
    with pytest.raises(ValueError):
        calculate_commission(0, 15.0)
    with pytest.raises(ValueError):
        calculate_commission(-100, 15.0)


def test_rejects_out_of_range_percent() -> None:
    with pytest.raises(ValueError):
        calculate_commission(1000, -1.0)
    with pytest.raises(ValueError):
        calculate_commission(1000, 101.0)
