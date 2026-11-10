"""Загрузка и валидация transactions.csv."""
import logging
import re
from datetime import datetime
from decimal import Decimal

import pandas as pd

log = logging.getLogger(__name__)

# Допущение: курса в данных нет, поэтому берём фиксированный (поменять можно здесь).
USD_TO_KGS = Decimal("87.5")
RATES = {"KGS": Decimal("1"), "USD": USD_TO_KGS}

DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M")
AMOUNT_RE = re.compile(r"-?\d+(\.\d+)?")


def parse_amount(raw):
    """'2 984,26' -> (Decimal('2984.26'), None). При ошибке -> (None, причина)."""
    text = raw.replace(" ", "").replace(",", ".")
    if not AMOUNT_RE.fullmatch(text):
        return None, "invalid_amount"
    value = Decimal(text)
    if value <= 0:
        return None, "non_positive_amount"
    return value, None


def parse_datetime(raw):
    """Пробуем оба формата, которые встретились в данных."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def validate_row(row):
    """Одна строка (dict из строк) -> (чистая строка, None) или (None, причина)."""
    for field in ("tx_id", "payer_id", "payee_id"):
        if not row[field]:
            return None, f"missing_{field}"

    amount, reason = parse_amount(row["amount"])
    if reason:
        return None, reason

    if row["currency"] not in RATES:
        return None, "unsupported_currency"

    tx_datetime = parse_datetime(row["tx_datetime"])
    if tx_datetime is None:
        return None, "invalid_datetime"

    if row["mcc"] and not row["mcc"].isdigit():
        return None, "invalid_mcc"
    mcc = row["mcc"].lstrip("0") or None  # '05812' -> '5812', пусто -> None

    amount_kgs = (amount * RATES[row["currency"]]).quantize(Decimal("0.01"))
    return {
        "tx_id": row["tx_id"],
        "payer_id": row["payer_id"],
        "payee_id": row["payee_id"],
        "amount": float(amount),
        "currency": row["currency"],
        "amount_kgs": float(amount_kgs),
        "mcc": mcc,
        "merchant": row["merchant"] or None,
        "tx_datetime": tx_datetime,
        "note": row["note"] or None,
    }, None


def split_duplicates(raw):
    """Дубли tx_id: полностью одинаковые -> оставляем первую; разные -> отбрасываем все копии."""
    uniq = raw.drop_duplicates()
    conflict_ids = set(uniq.loc[uniq.duplicated("tx_id", keep=False), "tx_id"])
    conflict = raw["tx_id"].isin(conflict_ids)
    exact_dup = raw.duplicated(keep="first") & ~conflict
    rejected = pd.concat([
        raw[conflict].assign(reason="conflicting_duplicate"),
        raw[exact_dup].assign(reason="duplicate_tx_id"),
    ])
    return raw[~conflict & ~exact_dup], rejected


def load_transactions(csv_path, rejected_path="rejected.csv"):
    """Читает CSV, возвращает DataFrame чистых операций, плохие строки пишет в rejected_path."""
    raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    raw = raw.apply(lambda col: col.str.strip())  # лишние пробелы в id и т.п.

    kept, rejected_dups = split_duplicates(raw)

    clean_rows, bad_rows = [], []
    for row in kept.to_dict("records"):
        clean, reason = validate_row(row)
        if reason:
            bad_rows.append({**row, "reason": reason})
        else:
            clean_rows.append(clean)

    rejected = pd.concat([rejected_dups, pd.DataFrame(bad_rows)], ignore_index=True)
    rejected.to_csv(rejected_path, index=False, encoding="utf-8")
    clean = pd.DataFrame(clean_rows)

    log.info("прочитано: %d, принято: %d, отброшено: %d", len(raw), len(clean), len(rejected))
    for reason, count in rejected["reason"].value_counts().items():
        log.info("  отброшено %s: %d", reason, count)
    return clean


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_transactions("data/transactions.csv")