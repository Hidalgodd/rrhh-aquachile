from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine

app = FastAPI(title="RRHH AquaChile")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        return {"db": conn.execute(text("SELECT 1")).scalar()}