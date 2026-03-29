from fastapi import FastAPI
from app.routes.upload import router as upload_router

app = FastAPI(title="AI-Driven API Governance System")

app.include_router(upload_router)

@app.get("/")
def read_root():
    return {"message": "Backend is running"}