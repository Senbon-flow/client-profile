from datetime import date

import pytest

from src.profile import UnknownClient, build_profile
from tests.helpers import load_rows, tx

MCC = {"5411": "groceries", "5812": "restaurants", "5541": "fuel"}
START, END = date(2026, 1, 1), date(2026, 6, 30)


def profile(tmp_path, rows, client="1001", start=START, end=END):
    clean, _ = load_rows(tmp_path, rows)
    return build_profile(client, start, end, transactions=clean, mcc_categories=MCC)


def test_self_transfer_is_ignored(tmp_path):
    rows = [
        tx("T1", "1001", "1001", "100000"),                # перевод самому себе
        tx("T2", "1001", "900001", "500", mcc="5411"),     # трата
        tx("T3", "800001", "1001", "2000"),                # входящая (зарплата)
    ]
    p = profile(tmp_path, rows)
    assert p["monthly"] == [{"month": "2026-03", "incoming": 2000.0, "outgoing": 500.0}]
    assert p["counterparties"] == 2  # сам клиент не контрагент себе


def test_monthly_sums_are_split_by_month(tmp_path):
    rows = [
        tx("T1", "800001", "1001", "1000", dt="2026-01-15 10:00:00"),
        tx("T2", "800001", "1001", "1500", dt="2026-01-20 10:00:00"),
        tx("T3", "1001", "900001", "300", dt="2026-02-01 10:00:00"),
    ]
    p = profile(tmp_path, rows)
    assert p["monthly"] == [
        {"month": "2026-01", "incoming": 2500.0, "outgoing": 0.0},
        {"month": "2026-02", "incoming": 0.0, "outgoing": 300.0},
    ]


def test_period_bounds_are_inclusive(tmp_path):
    rows = [
        tx("T1", "800001", "1001", "100", dt="2026-03-31 23:59:59"),  # последний день, входит
        tx("T2", "800001", "1001", "200", dt="2026-04-01 00:00:00"),  # на день позже, не входит
    ]
    p = profile(tmp_path, rows, start=date(2026, 3, 1), end=date(2026, 3, 31))
    assert p["monthly"] == [{"month": "2026-03", "incoming": 100.0, "outgoing": 0.0}]


def test_top3_categories_unknown_mcc_goes_to_other(tmp_path):
    rows = [
        tx("T1", "1001", "900001", "1000", mcc="5411"),
        tx("T2", "1001", "900002", "800", mcc="5812"),
        tx("T3", "1001", "900003", "700", mcc="1234"),   # нет в словаре -> other
        tx("T4", "1001", "900004", "100", mcc="5541"),   # четвёртая, в топ не попадёт
        tx("T5", "1001", "1002", "50000"),               # перевод человеку, без MCC -- не трата
    ]
    p = profile(tmp_path, rows)
    assert p["top_categories"] == [
        {"category": "groceries", "amount": 1000.0},
        {"category": "restaurants", "amount": 800.0},
        {"category": "other", "amount": 700.0},
    ]


def test_counterparties_are_counted_once(tmp_path):
    rows = [
        tx("T1", "1001", "900001", "100", mcc="5411"),
        tx("T2", "1001", "900001", "200", mcc="5411"),   # тот же торговец
        tx("T3", "800001", "1001", "5000"),
    ]
    assert profile(tmp_path, rows)["counterparties"] == 2


@pytest.mark.parametrize("client", ["9999", "900001"])  # нет в данных / торговец, а не клиент
def test_unknown_client_raises(tmp_path, client):
    rows = [tx("T1", "1001", "900001", "100", mcc="5411")]
    with pytest.raises(UnknownClient):
        profile(tmp_path, rows, client=client)