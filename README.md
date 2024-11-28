# importapi

## About

**importapi** is a Python application API designed to import and extract text from various sources, including:

- **txt** files
- **docx** files
- **PDF** files
- **URLs**

Extracted text is stored in JSON format in an S3 bucket.

---

## Run

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

Start the FastAPI app:

```bash
uvicorn main:app --reload
```

### Run Tests (Optional)

Execute the test suite:

```bash
pytest test_app.py
```
