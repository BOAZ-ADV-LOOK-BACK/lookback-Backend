import pytest
from app.db.database import SessionLocal, engine
from app.db.models import Base

@pytest.fixture(scope="module")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield SessionLocal
    Base.metadata.drop_all(bind=engine)
