# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import login, users, google, calendar

import os

app = FastAPI()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# API 라우터 등록 - 각각의 prefix를 명확하게 구분
app.include_router(login.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1/users")
app.include_router(google.router, prefix="/api/v1/google")
app.include_router(calendar.router, prefix="/api/v1/calendar")  # calendar는 /calendar prefix 사용

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to LookBack API"}