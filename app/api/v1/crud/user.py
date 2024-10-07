# CRUD operations for users
from sqlalchemy.orm import Session
from app.api.v1.models.user import User
from app.api.v1.schemas.user import UserCreate

def create_user(db: Session, user: UserCreate):
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user