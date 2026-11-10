"""HTTP-сервис: GET /clients/<id>/profile?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD"""
import re
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException

from src.profile import UnknownClient, build_profile

app = FastAPI(title="Client profile")

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_date(value, name):
    """'2026-03-15' -> date. Любая другая запись -> ответ 400."""
    if value is None or not DATE_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"{name}: ожидается формат YYYY-MM-DD")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:  # формат верный, но даты не существует, например 2026-02-30
        raise HTTPException(status_code=400, detail=f"{name}: такой даты не существует")


@app.get("/clients/{client_id}/profile")
def get_profile(client_id: str, date_from: Optional[str] = None, date_to: Optional[str] = None):
    start = parse_date(date_from, "date_from")
    end = parse_date(date_to, "date_to")
    if start > end:
        raise HTTPException(status_code=400, detail="date_from не может быть позже date_to")
    try:
        return build_profile(client_id, start, end)
    except UnknownClient:
        raise HTTPException(status_code=404, detail=f"клиент {client_id} не найден")