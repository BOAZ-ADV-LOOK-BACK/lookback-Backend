from sqlalchemy import Boolean, Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from app.db.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    google_id = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


    # 추가 필드들
    is_new_user = Column(Boolean, default=True)  # 신규 사용자 여부
    birth = Column(String, nullable=True)          # 생년월일
    gender = Column(String, nullable=True)        # 성별
    job = Column(String, nullable=True)           # 직업
    hobby = Column(String, nullable=True)         # 취미
    refresh_token = Column(String)