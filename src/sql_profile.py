"""Тот же расчёт «входящие и исходящие по месяцам», но на SQL (SQLite)."""
import sqlite3
from pathlib import Path

SQL_FILE = Path(__file__).resolve().parent.parent / "profile.sql"


def create_database(transactions, db_path=":memory:"):
    """Кладёт чистые операции в таблицу transactions и возвращает соединение."""
    conn = sqlite3.connect(db_path)
    table = transactions.copy()
    # SQLite не имеет типа «дата-время», поэтому храним текст 'YYYY-MM-DD HH:MM:SS'.
    table["tx_datetime"] = table["tx_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    table.to_sql("transactions", conn, if_exists="replace", index=False)
    return conn


def monthly_from_sql(conn, client_id, date_from, date_to):
    """Выполняет profile.sql. date_from и date_to -- объекты datetime.date."""
    query = SQL_FILE.read_text(encoding="utf-8")
    params = {
        "client_id": client_id,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }
    rows = conn.execute(query, params).fetchall()
    return [{"month": m, "incoming": i, "outgoing": o} for m, i, o in rows]


if __name__ == "__main__":
    import json
    import sys
    from datetime import date

    from src.profile import build_profile, get_transactions

    client = sys.argv[1]
    start, end = date(2026, 1, 1), date(2026, 6, 30)

    conn = create_database(get_transactions())
    from_sql = monthly_from_sql(conn, client, start, end)
    from_python = build_profile(client, start, end)["monthly"]

    print(json.dumps(from_sql, ensure_ascii=False, indent=2))
    print("совпадает с Python:", from_sql == from_python)