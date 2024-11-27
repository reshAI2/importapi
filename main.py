import os
import json
import uuid
import requests
import logging
import boto3
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from botocore.exceptions import BotoCoreError, NoCredentialsError
from unstructured.partition.auto import partition
from unstructured.partition.json import partition_json
# from unstructured.ingest.connector.confluence import ConfluenceAPI
from config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("Application is starting...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application is shutting down...")

# Настройки S3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

# Настройки Confluence
CONFLUENCE_BASE_URL = settings.confluence_base_url
CONFLUENCE_USERNAME = settings.confluence_username
CONFLUENCE_API_TOKEN = settings.confluence_api_token

@app.post("/process/")
async def process_file(file: UploadFile = File(...)):
    try:
        # Сохранение файла временно
        file_id = str(uuid.uuid4())
        temp_file_path = f"/tmp/{file_id}_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Обработка файла с Unstructured
        elements = partition(filename=temp_file_path)

        # Формирование JSON с текстом и метаинформацией
        result = {
            "file_name": file.filename,
            "file_id": file_id,
            "content": [element.to_dict() for element in elements],
        }

        # Сохранение JSON временно
        json_file_path = f"/tmp/{file_id}_export.json"
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, ensure_ascii=False, indent=4)

        # Загрузка JSON в S3
        s3_key = f"exports/{file_id}_export.json"
        s3_client.upload_file(json_file_path, S3_BUCKET_NAME, s3_key)

        # Удаление временных файлов
        os.remove(temp_file_path)
        os.remove(json_file_path)

        return {"message": "File processed and uploaded to S3 successfully", "s3_key": s3_key}
    except (BotoCoreError, NoCredentialsError) as e:
        return JSONResponse(content={"error": f"S3 Error: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/process-url/")
async def process_url(url: str):
    logger.info(f"Processing URL: {url}")
    try:
        # Загружаем содержимое по URL
        response = requests.get(url)
        response.raise_for_status()

        logger.info("Content fetched successfully from URL.")

        # Обработка содержимого через Unstructured
        elements = partition(text=response.text)

        # Формирование JSON
        file_id = str(uuid.uuid4())
        result = {
            "source": url,
            "file_id": file_id,
            "content": [element.to_dict() for element in elements],
        }

        # Сохранение JSON
        json_file_path = f"/tmp/{file_id}_export.json"
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, ensure_ascii=False, indent=4)

        logger.info("JSON file created. Uploading to S3...")
        # Загрузка JSON в S3
        s3_key = f"exports/{file_id}_url_export.json"
        s3_client.upload_file(json_file_path, S3_BUCKET_NAME, s3_key)

        # Удаление временного файла
        os.remove(json_file_path)
        logger.info(f"File successfully uploaded to S3: {s3_key}")

        return {"message": "URL processed and uploaded to S3 successfully", "s3_key": s3_key}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except (BotoCoreError, NoCredentialsError) as e:
        raise HTTPException(status_code=500, detail=f"S3 Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# @app.post("/process-confluence/")
# async def process_confluence(page_id: str):
#     try:
#         # Подключение к Confluence
#         confluence = ConfluenceAPI(
#             base_url=CONFLUENCE_BASE_URL,
#             username=CONFLUENCE_USERNAME,
#             api_token=CONFLUENCE_API_TOKEN,
#         )

#         # Получение содержимого страницы
#         page_content = confluence.get_page_content(page_id=page_id)

#         # Обработка содержимого через Unstructured
#         elements = partition(text=page_content)

#         # Формирование JSON
#         file_id = str(uuid.uuid4())
#         result = {
#             "source": f"Confluence page {page_id}",
#             "file_id": file_id,
#             "content": [element.to_dict() for element in elements],
#         }

#         # Сохранение JSON
#         json_file_path = f"/tmp/{file_id}_export.json"
#         with open(json_file_path, "w", encoding="utf-8") as json_file:
#             json.dump(result, json_file, ensure_ascii=False, indent=4)

#         # Загрузка JSON в S3
#         s3_key = f"exports/{file_id}_confluence_export.json"
#         s3_client.upload_file(json_file_path, S3_BUCKET_NAME, s3_key)

#         # Удаление временного файла
#         os.remove(json_file_path)

#         return {"message": "Confluence page processed and uploaded to S3 successfully", "s3_key": s3_key}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing Confluence page: {str(e)}")
