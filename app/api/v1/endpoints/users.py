from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.v1.schemas.user import UserCreate, UserInDB
from app.api.v1.crud.user import create_user
from app.db.database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/users/", response_model=UserInDB)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Attempting to create user with data: {user.dict()}")
        new_user = create_user(db, user)
        logger.info(f"User created successfully: {new_user.dict()}")
        return new_user
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Unable to create user: {str(e)}")