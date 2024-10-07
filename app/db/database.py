from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os 
from dotenv import load_dotenv

load_dotenv()

DB_PWD = os.environ.get("DB_PWD")

SQLALCHEMY_DATABASE_URL = f"mysql://ubuntu:{DB_PWD}@localhost:3306/lookback"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()