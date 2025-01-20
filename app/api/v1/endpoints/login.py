from datetime import timedelta
import traceback
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import json
import logging
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
from app.db.dynamo import put_calendar_list
from app.api.v1.endpoints import google

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)
router = APIRouter()

class GoogleAuthRequest(BaseModel):
   """
   Google 인증 요청을 위한 모델

   Attributes:
       code (str): Google OAuth2 인증 코드
   """
   code: str

async def get_or_create_user(
   db: AsyncSession, 
   email: str, 
   name: str, 
   google_id: str, 
   refresh_token: str = None
) -> tuple[User, bool]:
   """
   주어진 이메일로 사용자를 조회하거나 새로 생성합니다.

   Args:
       db (AsyncSession): 데이터베이스 세션
       email (str): 사용자 이메일
       name (str): 사용자 이름
       google_id (str): Google 계정 ID
       refresh_token (str, optional): Google OAuth2 리프레시 토큰

   Returns:
       tuple[User, bool]: (사용자 객체, 새로운 사용자 여부)
   """
   result = await db.execute(select(User).where(User.email == email))
   user = result.scalar_one_or_none()

   if user is None:
       user = User(
           email=email,
           full_name=name,
           google_id=google_id,
           refresh_token=refresh_token,
           is_new_user=True
       )
       db.add(user)
       await db.commit()
       await db.refresh(user)
       return user, True

   if refresh_token:
       user.refresh_token = refresh_token
       await db.commit()
       await db.refresh(user)

   return user, False

@router.post("/login")
async def google_login(
   auth_request: GoogleAuthRequest,
   db: AsyncSession = Depends(get_db)
):
   """
   Google OAuth2를 통한 사용자 로그인을 처리합니다.

   Args:
       auth_request (GoogleAuthRequest): Google 인증 요청 정보
       db (AsyncSession): 데이터베이스 세션

   Returns:
       dict: 로그인 결과 정보 (토큰, 사용자 정보 등)

   Raises:
       HTTPException: 로그인 처리 중 오류 발생 시
   """
   try:
       logger.info("로그인 프로세스 시작")
       token_info = await google.get_access_token(auth_request.code)
       logger.info("구글 토큰 정보 수신 완료")
       
       async with httpx.AsyncClient() as client:
           logger.info("구글에서 사용자 정보 요청 중")
           user_info_response = await client.get(
               "https://www.googleapis.com/oauth2/v2/userinfo",
               headers={"Authorization": f"Bearer {token_info['access_token']}"}
           )
           user_info = user_info_response.json()
           logger.info(f"사용자 정보 수신 완료. 이메일: {user_info.get('email')}")
           
           try:
               user, is_new_user = await get_or_create_user(
                   db,
                   email=user_info["email"],
                   name=user_info["name"],
                   google_id=user_info["id"],
                   refresh_token=token_info.get('refresh_token')
               )
               logger.info(f"사용자 {'생성' if is_new_user else '조회'} 완료")
           except Exception as e:
               logger.error(f"사용자 정보 처리 중 오류 발생: {str(e)}")
               logger.error(f"상세 에러: {traceback.format_exc()}")
               raise
           
           access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
           access_token = create_access_token(
               data={"sub": user.email},
               expires_delta=access_token_expires
           )
           logger.info("JWT 토큰 생성 완료")
           
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
       logger.error(f"로그인 중 오류 발생: {str(e)}")
       logger.error(f"상세 에러 정보: {traceback.format_exc()}")
       raise HTTPException(status_code=500, detail=str(e))