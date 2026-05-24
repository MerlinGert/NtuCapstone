# CryptoVis Backend

This is a FastAPI backend for processing data and serving API requests.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    Or use uv:
    ```bash
    uv sync
    ```

## Running the Server

Run the server from `front/server`:

```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8099
```

The API will be available at `http://127.0.0.1:8099`.
Frontend requests to `/api/*` will be proxied to this server.

## Structure

- `main.py`: The FastAPI application entry point.
- `requirements.txt`: Python dependencies.
- `../data_processing/`: Data processing scripts (available in python path).
