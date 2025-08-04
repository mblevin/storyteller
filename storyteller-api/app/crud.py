from sqlalchemy.orm import Session
from . import database

def create_story(db: Session, prompt: str, story_text: str, audio_url: str):
    db_story = database.StoryDB(prompt=prompt, story_text=story_text, audio_url=audio_url)
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story
