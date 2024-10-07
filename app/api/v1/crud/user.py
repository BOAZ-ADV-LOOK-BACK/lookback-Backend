# app/api/v1/crud/user.py

from sqlalchemy.orm import Session
from app.api.v1.models.user import User  # SQLAlchemy 모델을 import
from app.api.v1.schemas.user import UserCreate

def create_user(db: Session, user: UserCreate):
    db_user = User(
        email=user.email,
        username=user.username,
        age=user.age,
        gender=user.gender,
        job=user.job,
        hobby=user.hobby
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
