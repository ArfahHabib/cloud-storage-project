# Backend API — Anila Kiran

## Setup
```bash
cd cloud-storage-project
pip install -r backend/requirements.txt -r security/requirements.txt -r storage/requirements.txt
```

## Run the API server
```bash
python -m backend.app
```
Server starts at: http://localhost:5000

## Test it's working
Open your browser and go to: http://localhost:5000/api/ping
You should see: `{"status": "ok", "message": "Cloud Storage API is running ✅"}`

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/ping | Health check (no auth) |
| GET | /api/health | S3 bucket status |
| POST | /api/upload | Upload + encrypt a file |
| GET | /api/files | List your files |
| GET | /api/download/<id> | Download + decrypt |
| DELETE | /api/files/<id> | Delete a file |

## Dev Mode Testing (no Cognito needed)
Pass `Authorization: Bearer dev-testuser` header to bypass Cognito.

## Files
- `app.py` — Flask routes (the coordinator)
- `auth.py` — Cognito JWT token verification
- `database.py` — DynamoDB operations
