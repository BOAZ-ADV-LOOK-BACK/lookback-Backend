from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
async def read_users():
    return {"users": "This is a list of users"}
