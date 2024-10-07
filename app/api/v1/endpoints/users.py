from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.schemas.user import UserCreate, UserInDB
from app.api.v1.crud.user import create_user
from app.db.database import get_db

router = APIRouter()

@router.post("/users/", response_model=UserInDB)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)