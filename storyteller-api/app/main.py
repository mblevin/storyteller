from fastapi import FastAPI, HTTPException, Depends
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

@app.post("/stories", response_model=models.StoryResponse)
def create_story(request: models.StoryRequest, db: Session = Depends(get_db)):
    """
    Accepts a text prompt, generates a story, converts it to audio,
    and returns the URL to the audio file.
    """
    try:
        story_text = services.generate_story_text(request.prompt)
        audio_url = services.convert_text_to_audio(story_text)
        
        crud.create_story(
            db=db,
            prompt=request.prompt,
            story_text=story_text,
            audio_url=audio_url
        )
        
        return models.StoryResponse(story_text=story_text, audio_url=audio_url)
    except Exception as e:
        # Basic error handling
        raise HTTPException(status_code=500, detail=str(e))
