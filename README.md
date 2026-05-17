# Conversational SHL Assessment Recommender

FastAPI service for the SHL Labs take-home assignment. The API is stateless and only recommends assessments from a locally scraped SHL Individual Test Solutions catalog snapshot.

## Run in VS Code

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\scrape_catalog.py
uvicorn app.main:app --reload --port 8000
```

Then open:

- **Chat UI:** http://127.0.0.1:8000/
- API info (JSON): http://127.0.0.1:8000/api
- Health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs
- Chat API: `POST http://127.0.0.1:8000/chat`

The frontend lives in `frontend/` and is served at the site root (`/`).

## Example

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{
  "messages": [
    {"role": "user", "content": "Hiring a mid-level Java developer who works with stakeholders. Add personality too."}
  ]
}'
```

## Tests

```powershell
pytest
```

## Deploy on Render

1. Push this folder to GitHub.
2. In Render, create a new Web Service from that repository.
3. Use the included `render.yaml`, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
4. Submit the Render public URL for the assignment (e.g. `https://<your-service>.onrender.com/`).
