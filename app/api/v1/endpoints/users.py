# users.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.api.deps import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class UserAdditionalInfo(BaseModel):
    email: str
    birth: str
    gender: str
    job: str
    hobby: str
    interest: Optional[str] = None  # interest 필드 추가

class UserProfileUpdate(BaseModel):
    occupation: Optional[str] = None
    interest: Optional[str] = None
    hobby: Optional[str] = None

@router.get("/profile")
async def get_user_profile(email: str, db: AsyncSession = Depends(get_db)):
    """현재 로그인한 사용자의 프로필 정보를 조회합니다."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "name": user.full_name,
        "email": user.email,
        "birthDate": user.birth,
        "gender": user.gender,
        "occupation": user.job,
        "interest": user.interest if hasattr(user, 'interest') else None,
        "hobby": user.hobby
    }

@router.patch("/profile")
async def update_profile(
    profile_update: UserProfileUpdate,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인한 사용자의 프로필 정보를 수정합니다."""
    try:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 수정 가능한 필드 업데이트
        if profile_update.occupation is not None:
            user.job = profile_update.occupation
        if profile_update.interest is not None:
            user.interest = profile_update.interest
        if profile_update.hobby is not None:
            user.hobby = profile_update.hobby

        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "message": "프로필이 성공적으로 업데이트되었습니다.",
            "data": {
                "name": user.full_name,
                "email": user.email,
                "birthDate": user.birth,
                "gender": user.gender,
                "occupation": user.job,
                "interest": user.interest if hasattr(user, 'interest') else None,
                "hobby": user.hobby
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="프로필 업데이트 중 오류가 발생했습니다."
        )

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """JWT 토큰으로 현재 로그인한 사용자의 이메일을 반환합니다."""
    logger.info(f"'me' 엔드포인트 호출됨: {current_user.email}")
    
    return {
        "email": current_user.email
    }

# @router.get("/get-user-email")
# async def get_user_email(email: str, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.email == email))
#     user = result.scalar_one_or_none()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return {"email": user.email}

@router.get("/get-user-info")
async def get_user_info(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = {
        "full_name": user.full_name,
        "email": user.email,
        "birth": user.birth,
        "gender": user.gender,
        "job": user.job,
        "hobby": user.hobby,
        "interest": user.interest if hasattr(user, 'interest') else None,
        "is_new_user": user.is_new_user,
    }

    logger.info(f"Returning user data: {user_data}")
    return user_data

@router.post("/update-user-info")
async def update_user_info(
    user_info: UserAdditionalInfo,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(User).where(User.email == user_info.email)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.birth = user_info.birth
        user.gender = user_info.gender
        user.job = user_info.job
        user.hobby = user_info.hobby
        user.interest = user_info.interest
        user.is_new_user = False

        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "message": "User information updated successfully",
            "data": {
                "birth": user.birth,
                "gender": user.gender,
                "job": user.job,
                "hobby": user.hobby,
                "interest": user.interest
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while updating user information.")