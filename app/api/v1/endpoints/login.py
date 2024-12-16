# look-back 서비스 로그인 관련

from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import json
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
from app.db.dynamo import put_calendar_list
from app.api.v1.endpoints import google

import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)
router = APIRouter()

class GoogleAuthRequest(BaseModel):
    code: str

async def get_or_create_user(db: AsyncSession, email: str, name: str, google_id: str) -> tuple[User, bool]:
    # 기존 사용자 검색
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # 새 사용자 생성
        user = User(
            email=email,
            full_name=name,
            google_id=google_id,
            is_new_user=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user, True

    return user, False

@router.post("/login")
async def google_login(
    auth_request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 구글 access token과 refresh token 획득
        token_info = await google.get_access_token(auth_request.code)
        
        async with httpx.AsyncClient() as client:
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_info['access_token']}"}
            )
            user_info = user_info_response.json()
            
            # 사용자 생성 또는 업데이트
            user, is_new_user = await get_or_create_user(
                db,
                email=user_info["email"],
                name=user_info.get("name", ""),
                google_id=user_info["id"],
                refresh_token=token_info.get('refresh_token')  # refresh token 저장
            )
            
            # JWT 토큰 생성
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.email},
                expires_delta=access_token_expires
            )
            
            return {
                "success": True,
                "access_token": access_token,
                "token_type": "bearer",
                "isNewUser": is_new_user,
                "user": {
                    "email": user.email,
                    "name": user.full_name,
                    "picture": user_info.get("picture", "")
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))