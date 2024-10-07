# app/api/v1/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    age: int | None = None
    gender: str | None = None
    job: str | None = None
    hobby: str | None = None

class UserInDB(UserCreate):
    class Config:
        orm_mode = True
