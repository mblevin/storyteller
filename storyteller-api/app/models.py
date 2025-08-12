from pydantic import BaseModel

class StoryRequest(BaseModel):
    prompt: str

class StoryTaskResponse(BaseModel):
    task_id: int
    status: str

class StoryStatusResponse(BaseModel):
    task_id: int
    status: str
    audio_url: str | None = None
    story_text: str | None = None

class StorySection(BaseModel):
    story_section_text: str

class Story(BaseModel):
    id: int
    prompt: str
    story_text: str | None = None
    audio_url: str | None = None
    status: str = "pending"

    class Config:
        from_attributes = True
