# app/api/v1/endpoints/token.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

# 요청 본문에 필요한 데이터 스키마 정의
class TokenData(BaseModel):
    access_token: str

@router.post("/save-token")
async def save_token(token_data: TokenData):
    # 액세스 토큰 출력 (DB 저장이나 추가 작업을 여기에 작성)
    print(f"Received Access Token: {token_data.access_token}")

    # 여기에 액세스 토큰 저장 로직 추가 (예: 데이터베이스에 저장)
    # 예시: db.save_token(token_data.access_token)

    return {"message": "Token received and processed"}
