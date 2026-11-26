import os

from sqlalchemy import URL

DB_URL = os.getenv("DATABASE_URL") or URL.create(
    "postgresql+psycopg",
    username=os.getenv("DB_USER", "dispatch"),
    password=os.getenv("DB_PASSWORD", "demo-ropeway-local"),
    host=os.getenv("DB_HOST", "127.0.0.1"),
    database=os.getenv("DB_NAME", "ropeway"),
)
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
JWT_SECRET = os.getenv("JWT_SECRET", "local-ropeway-shadow-panel-signing-key")
SEED_DEMO = os.getenv("SEED_DEMO", "false").lower() == "true"
QUEUE_KEY = "ropeway:panel:candidates"
DEMO_PASSWORD = "CabinTrial2026!"
