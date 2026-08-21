import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_is_logged(caplog):
    with caplog.at_level(logging.INFO, logger="kyomei_api"):
        response = client.get("/health")
    assert response.status_code == 200
    assert any(record.name == "kyomei_api" and "/health" in record.getMessage() for record in caplog.records)
