import pytest
from fastapi.testclient import TestClient

from src.app import app
from tests.helpers import load_rows, tx

client = TestClient(app)
GOOD = {"date_from": "2026-01-01", "date_to": "2026-06-30"}


@pytest.fixture
def small_data(tmp_path, monkeypatch):
    """Подменяет настоящие данные маленькими, чтобы тесты не зависели от файлов в data/."""
    df, _ = load_rows(tmp_path, [tx("T1", "1001", "900001", "500", mcc="5411")])
    monkeypatch.setattr("src.profile.get_transactions", lambda: df)
    monkeypatch.setattr("src.profile.get_mcc_categories", lambda: {"5411": "groceries"})


@pytest.mark.parametrize("params", [
    {"date_from": "2026-13-40", "date_to": "2026-06-30"},   # несуществующая дата
    {"date_from": "01.01.2026", "date_to": "2026-06-30"},   # не тот формат
    {"date_from": "2026-06-30", "date_to": "2026-01-01"},   # начало позже конца
    {"date_from": "2026-01-01"},                            # нет date_to
])
def test_invalid_date_returns_400(params):
    response = client.get("/clients/1001/profile", params=params)
    assert response.status_code == 400


def test_unknown_client_returns_404(small_data):
    assert client.get("/clients/9999/profile", params=GOOD).status_code == 404


def test_merchant_id_is_not_a_client(small_data):
    assert client.get("/clients/900001/profile", params=GOOD).status_code == 404


def test_known_client_returns_profile(small_data):
    response = client.get("/clients/1001/profile", params=GOOD)
    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "1001"
    assert body["top_categories"] == [{"category": "groceries", "amount": 500.0}]