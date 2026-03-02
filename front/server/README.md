# CryptoVis Backend

This is a FastAPI backend for processing data and serving API requests.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Server

Run the server from the project root (`code/front`):

```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Frontend requests to `/api/*` will be proxied to this server.

## Structure

- `main.py`: The FastAPI application entry point.
- `requirements.txt`: Python dependencies.
- `../data_processing/`: Data processing scripts (available in python path).
