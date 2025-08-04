from pydantic import BaseModel

class StoryRequest(BaseModel):
    prompt: str

class StoryResponse(BaseModel):
    story_text: str
    audio_url: str

class Story(BaseModel):
    id: int
    prompt: str
    story_text: str
    audio_url: str

    class Config:
        from_attributes = True
