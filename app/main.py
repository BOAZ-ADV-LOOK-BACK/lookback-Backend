from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.get_authorization import router as auth_router
from app.api.v1.endpoints.data_preprocessing import router as preprocess_router
from app.api.v1.endpoints import login
import os

app = FastAPI()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app.include_router(preprocess_router, prefix='/preprocess')
app.include_router(login.router, prefix="/api/v1")

# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify the domain(s) you want to allow
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 나머지 FastAPI 애플리케이션 설정
@app.get("/")
async def root():
    return {"message": "Welcome to LookBack API"}