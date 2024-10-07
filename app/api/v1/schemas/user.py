# app/api/v1/crud/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    age: int | None = None
    gender: str | None = None
    job: str | None = None
    hobby: str | None = None

class UserInDB(UserCreate):
    class Config:
        from_attributes = True