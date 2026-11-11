from datetime import datetime

import pytest

from src.loader import USD_TO_KGS
from tests.helpers import load_rows, tx


def test_exact_duplicate_tx_id_keeps_only_first(tmp_path):
    rows = [tx("T1", "1001", "900001", "100"), tx("T1", "1001", "900001", "100")]
    clean, rejected = load_rows(tmp_path, rows)
    assert len(clean) == 1
    assert list(rejected["reason"]) == ["duplicate_tx_id"]


def test_conflicting_duplicate_rejects_both_copies(tmp_path):
    rows = [tx("T1", "1001", "900001", "9266.76"), tx("T1", "1001", "900001", "92668.60")]
    clean, rejected = load_rows(tmp_path, rows)
    assert len(clean) == 0
    assert list(rejected["reason"]) == ["conflicting_duplicate", "conflicting_duplicate"]


@pytest.mark.parametrize("amount, dt, reason", [
    ("n/a", "2026-03-10 12:00:00", "invalid_amount"),
    ("", "2026-03-10 12:00:00", "invalid_amount"),
    ("0", "2026-03-10 12:00:00", "non_positive_amount"),
    ("-50", "2026-03-10 12:00:00", "non_positive_amount"),
    ("100", "yesterday", "invalid_datetime"),
    ("100", "2026-02-30 12:00:00", "invalid_datetime"),
])
def test_invalid_row_is_rejected_with_reason(tmp_path, amount, dt, reason):
    clean, rejected = load_rows(tmp_path, [tx("T1", "1001", "900001", amount, dt=dt)])
    assert len(clean) == 0
    assert list(rejected["reason"]) == [reason]


def test_messy_but_recoverable_values_are_cleaned(tmp_path):
    rows = [tx("T1", " 1003 ", "900001", "2 984,26", mcc="05812", dt="03.04.2026 10:15")]
    clean, rejected = load_rows(tmp_path, rows)
    assert len(rejected) == 0
    row = clean.iloc[0]
    assert row.payer_id == "1003"
    assert row.amount_kgs == 2984.26
    assert row.mcc == "5812"
    assert row.tx_datetime == datetime(2026, 4, 3, 10, 15)


def test_usd_is_converted_to_kgs(tmp_path):
    clean, _ = load_rows(tmp_path, [tx("T1", "1001", "900001", "10", currency="USD")])
    assert clean.iloc[0].amount_kgs == float(10 * USD_TO_KGS)