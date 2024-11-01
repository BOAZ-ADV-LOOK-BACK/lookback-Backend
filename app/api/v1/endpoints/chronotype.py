# [KAN-39] 참새족/올빼미족 컴포넌트 생성

from fastapi import APIRouter

router = APIRouter()

@router.get("/items")
async def read_items():
    return {"items": "This is a list of items"}