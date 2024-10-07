from sqlalchemy import Column, Integer, String
from app.db.database import Base  # Base는 SQLAlchemy의 declarative_base로 생성한 인스턴스

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    age = Column(Integer)
    gender = Column(String)
    job = Column(String)
    hobby = Column(String)