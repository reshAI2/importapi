import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app  # Импорт приложения из файла main.py

client = TestClient(app)

# Тестовые данные
TEST_URL = "https://example.com"
TEST_PAGE_ID = "12345"
MOCK_S3_KEY = "exports/mock_file.json"

@pytest.fixture
def mock_s3_upload():
    """Мок для загрузки файла в S3"""
    with patch("app.s3_client.upload_file") as mock_upload:
        mock_upload.return_value = None
        yield mock_upload

@pytest.fixture
def mock_requests_get():
    """Мок для requests.get"""
    with patch("app.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "Mocked response content"
        yield mock_get

# @pytest.fixture
# def mock_confluence_api():
#     """Мок для ConfluenceAPI"""
#     with patch("app.ConfluenceAPI") as MockConfluenceAPI:
#         instance = MockConfluenceAPI.return_value
#         instance.get_page_content.return_value = "Mocked Confluence content"
#         yield instance

def test_process_url(mock_s3_upload, mock_requests_get):
    response = client.post("/process-url/", json={"url": TEST_URL})
    assert response.status_code == 200
    assert response.json()["s3_key"].startswith("exports/")

    # Проверяем, что загрузка в S3 была вызвана
    mock_s3_upload.assert_called_once()

# def test_process_confluence(mock_s3_upload, mock_confluence_api):
#     response = client.post("/process-confluence/", json={"page_id": TEST_PAGE_ID})
#     assert response.status_code == 200
#     assert response.json()["s3_key"].startswith("exports/")

#     # Проверяем, что загрузка в S3 была вызвана
#     mock_s3_upload.assert_called_once()
#     mock_confluence_api.get_page_content.assert_called_once_with(page_id=TEST_PAGE_ID)

def test_invalid_url(mock_requests_get):
    mock_requests_get.side_effect = Exception("Invalid URL")
    response = client.post("/process-url/", json={"url": "invalid_url"})
    assert response.status_code == 400
    assert "Failed to fetch URL" in response.json()["detail"]

# def test_invalid_confluence_page(mock_confluence_api):
#     mock_confluence_api.get_page_content.side_effect = Exception("Page not found")
#     response = client.post("/process-confluence/", json={"page_id": "invalid_page"})
#     assert response.status_code == 500
#     assert "Error processing Confluence page" in response.json()["detail"]
