from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:////var/data/storyteller.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Define the Story table model
class StoryDB(Base):
    __tablename__ = "stories"
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(String)
    story_text = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)
    status = Column(String, default="pending")

def init_db():
    Base.metadata.create_all(bind=engine)
