from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User

router = APIRouter()

class UserAdditionalInfo(BaseModel):
    email: str
    birth: str
    gender: str
    job: str
    hobby: str

@router.get("/get-user-email")
async def get_user_email(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"email": user.email}

@router.get("/get-user-info")
async def get_user_info(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": user.email,
        "birth": user.birth,
        "gender": user.gender,
        "job": user.job,
        "hobby": user.hobby,
    }

@router.post("/update-user-info")
async def update_user_info(
    user_info: UserAdditionalInfo,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 이메일을 기준으로 사용자 찾기
        result = await db.execute(
            select(User).where(User.email == user_info.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 추가 정보 업데이트
        user.birth = user_info.birth
        user.gender = user_info.gender
        user.job = user_info.job
        user.hobby = user_info.hobby
        user.is_new_user = False  # 추가 정보를 입력했으므로 더 이상 새 사용자가 아님

        # 데이터베이스 커밋 및 새 값 반영
        await db.commit()
        await db.refresh(user)

        return {
            "success": True,
            "message": "User information updated successfully",
            "data": {
                "birth": user.birth,
                "gender": user.gender,
                "job": user.job,
                "hobby": user.hobby
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while updating user information.")