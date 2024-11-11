from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info("Starting login process")
        token_url = "https://oauth2.googleapis.com/token"

        with open("client_secret_639048076528-0mqbo91cf5t0fq5604u0tblqnaka8thp.apps.googleusercontent.com.json", "r") as f:
            client_config = json.load(f)["web"]

        token_data = {
            "code": auth_request.code,
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()

            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_info['access_token']}"}
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()

            # DB에서 사용자 조회 또는 생성
            user, is_new_user = await get_or_create_user(
                db,
                email=user_info["email"],
                name=user_info.get("name", ""),
                google_id=user_info["id"]
            )

            return {
                "success": True,
                "isNewUser": is_new_user,
                "user": {
                    "email": user.email,
                    "name": user.full_name,
                    "picture": user_info.get("picture", "")
                }
            }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error during Google API call: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"구글 인증 실패: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"내부 서버 오류: {str(e)}"
        )