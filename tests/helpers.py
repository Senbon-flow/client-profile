"""Общие помощники для тестов: быстро собрать маленький CSV и прогнать через загрузчик."""
import csv

import pandas as pd

from src.loader import load_transactions

COLUMNS = ["tx_id", "payer_id", "payee_id", "amount", "currency",
           "mcc", "merchant", "tx_datetime", "note"]


def tx(tx_id, payer, payee, amount, currency="KGS", mcc="", merchant="",
       dt="2026-03-10 12:00:00", note=""):
    """Одна строка CSV в виде словаря. Всё, что не указали, заполняется обычными значениями."""
    return dict(zip(COLUMNS, [tx_id, payer, payee, amount, currency, mcc, merchant, dt, note]))


def load_rows(tmp_path, rows):
    """Пишет строки во временный CSV, загружает его и возвращает (чистые, отброшенные)."""
    csv_path = tmp_path / "transactions.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    rejected_path = tmp_path / "rejected.csv"
    clean = load_transactions(csv_path, rejected_path)
    rejected = pd.read_csv(rejected_path, dtype=str, keep_default_na=False)
    return clean, rejected