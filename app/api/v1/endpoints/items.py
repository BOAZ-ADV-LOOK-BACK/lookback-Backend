from fastapi import APIRouter

router = APIRouter()

@router.get("/items")
async def read_items():
    return {"items": "This is a list of items"}
