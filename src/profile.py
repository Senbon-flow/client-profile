"""Профиль клиента: доходы и расходы по месяцам, топ категорий, контрагенты."""
import json
from functools import lru_cache

from src.loader import load_transactions


class UnknownClient(Exception):
    """Такого клиента нет в данных."""


@lru_cache(maxsize=1)
def get_transactions():
    """Чистые операции читаем из файла один раз и запоминаем."""
    return load_transactions("data/transactions.csv")


@lru_cache(maxsize=1)
def get_mcc_categories():
    with open("data/mcc_categories.json", encoding="utf-8") as f:
        return json.load(f)


def build_profile(client_id, date_from, date_to, transactions=None, mcc_categories=None):
    """date_from и date_to -- объекты datetime.date, обе границы включительно."""
    df = get_transactions() if transactions is None else transactions
    mcc_categories = get_mcc_categories() if mcc_categories is None else mcc_categories

    # Все операции клиента (в любую сторону).
    mine = df[(df.payer_id == client_id) | (df.payee_id == client_id)]
    if mine.empty:
        raise UnknownClient(client_id)

    # Переводы самому себе не считаем: это не доход и не расход.
    mine = mine[mine.payer_id != mine.payee_id]

    # Только нужный период.
    day = mine.tx_datetime.dt.date
    mine = mine[(day >= date_from) & (day <= date_to)]

    outgoing = mine[mine.payer_id == client_id]
    incoming = mine[mine.payee_id == client_id]

    # 1. Входящие и исходящие по месяцам.
    months = {}
    for name, part in (("incoming", incoming), ("outgoing", outgoing)):
        sums = part.groupby(part.tx_datetime.dt.strftime("%Y-%m")).amount_kgs.sum()
        for month, total in sums.items():
            row = months.setdefault(month, {"month": month, "incoming": 0.0, "outgoing": 0.0})
            row[name] = round(float(total), 2)
    monthly = [months[month] for month in sorted(months)]

    # 2. Топ-3 категории трат: исходящие с непустым MCC, неизвестный MCC -> "other".
    spend = outgoing[outgoing.mcc.notna()]
    category = spend.mcc.map(lambda mcc: mcc_categories.get(mcc, "other"))
    totals = spend.groupby(category).amount_kgs.sum()
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[:3]
    top_categories = [{"category": name, "amount": round(float(total), 2)} for name, total in ranked]

    # 3. Уникальные контрагенты: кому клиент платил и от кого получал.
    counterparties = set(outgoing.payee_id) | set(incoming.payer_id)

    return {
        "client_id": client_id,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "monthly": monthly,
        "top_categories": top_categories,
        "counterparties": len(counterparties),
    }


if __name__ == "__main__":
    import sys
    from datetime import date

    result = build_profile(sys.argv[1], date(2026, 1, 1), date(2026, 6, 30))
    print(json.dumps(result, ensure_ascii=False, indent=2))