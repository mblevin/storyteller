from sqlalchemy.orm import Session
from . import database

def create_story_task(db: Session, prompt: str):
    """Creates an initial record for a story generation task."""
    db_story = database.StoryDB(prompt=prompt, status="pending")
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story

def get_story(db: Session, story_id: int):
    """Gets a story by its ID."""
    return db.query(database.StoryDB).filter(database.StoryDB.id == story_id).first()

def update_story_status(db: Session, story_id: int, status: str):
    """Updates the status of a story."""
    db_story = get_story(db, story_id)
    if db_story:
        db_story.status = status
        db.commit()
        db.refresh(db_story)
    return db_story

def complete_story(db: Session, story_id: int, story_text: str, audio_url: str):
    """Marks a story as complete and saves the final data."""
    db_story = get_story(db, story_id)
    if db_story:
        db_story.story_text = story_text
        db_story.audio_url = audio_url
        db_story.status = "complete"
        db.commit()
        db.refresh(db_story)
    return db_story
