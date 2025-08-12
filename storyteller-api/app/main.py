import os
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from . import models, services, crud, database

app = FastAPI()

# Dependency to get a DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    database.init_db()

@app.post("/stories", response_model=models.StoryTaskResponse)
async def create_story_task(
    request: models.StoryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Accepts a prompt and starts a background task to generate the story.
    Returns a task ID to check for status.
    """
    new_story = crud.create_story_task(db=db, prompt=request.prompt)
    background_tasks.add_task(
        services.generate_story_and_audio,
        story_id=new_story.id,
        prompt=request.prompt
    )
    return {"task_id": new_story.id, "status": "pending"}

@app.get("/stories/{story_id}", response_model=models.StoryStatusResponse)
def get_story_status(story_id: int, db: Session = Depends(get_db)):
    """
    Checks the status of a story generation task.
    """
    story = crud.get_story(db=db, story_id=story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return {
        "task_id": story.id,
        "status": story.status,
        "audio_url": story.audio_url,
        "story_text": story.story_text
    }
