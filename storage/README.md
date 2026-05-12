# Storage Module — Abdullah Waheed

## Setup
```bash
cd storage
pip install -r requirements.txt
```

## Test your storage (sharding only — no AWS needed)
```bash
python shard_manager.py
```

## Test with AWS (requires .env configured)
Make sure your `.env` file has the correct bucket names, then run:
```bash
python shard_manager.py
```
You should see both S3 buckets as ✅ healthy.

## Files
- `shard_manager.py` — All S3 upload/download/health check logic.
