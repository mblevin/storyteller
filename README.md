# Storyteller MVP: Implementation Plan

## 1. Project Status

- [x] **Phase 1: Backend Setup**
- [x] **Phase 2: AI & Database Integration** (TTS Implemented)
- [x] **Phase 2.5: Story Generation Validation**
- [ ] **Phase 3: Frontend Setup**
- [ ] **Phase 4: Frontend-Backend Integration**
- [x] **Phase 5: Deployment**

---

## 2. Project Objective

This document outlines the steps to build the Minimum Viable Product (MVP) for the Storyteller application. The goal is a functional iPad app that allows a user to provide a spoken prompt, which is then used to generate and play a 30-minute audio sleep story.

## 3. Technology Stack

- **Frontend:** Swift, SwiftUI (for native iPadOS application)
- **Backend:** Python, FastAPI (for web server)
- **Speech-to-Text (STT):** OpenAI Whisper (running on-device via `whisper.cpp`)
- **Language Model (LLM):** Google Gemini 2.5 Pro API
- **Text-to-Speech (TTS):** Google Cloud Text-to-Speech API (Voice: `en-US-Wavenet-F`)
- **Database:** SQLite (for MVP storage)
- **Hosting:** Render (free tier)

---

## 4. Phase 1: Backend Setup (Python/FastAPI)

### 3.1. Directory Structure

Create the following directory structure for the backend server inside the `storyteller` git repository.

```
storyteller-api/
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI app definition
│   ├── models.py       # Pydantic data models
│   ├── database.py     # Database connection and setup
│   ├── crud.py         # Database create/read operations
│   └── services.py     # Logic for AI service interactions
├── .env                # For local environment variables
└── requirements.txt    # Project dependencies
```

### 3.2. Environment Setup

1.  **Create `.env` file:** For local development, create a `.env` file in the `storyteller-api` root. Add your Google API key to it. This file should be added to `.gitignore`.
    ```
    # .env
    GEMINI_API_KEY="your_api_key_here"
    ```
2.  **Create `requirements.txt`:**
    ```
    fastapi
    uvicorn[standard]
    pydantic
    sqlalchemy
    requests
    python-dotenv
    google-cloud-storage
    ```
3.  **Install dependencies:** `pip install -r requirements.txt`

### 3.3. API Endpoint Definition

In `app/main.py`, define the primary API endpoint.

```python
# app/main.py
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
        
        return models.StoryResponse(audio_url=audio_url)
    except Exception as e:
        # Basic error handling
        raise HTTPException(status_code=500, detail=str(e))
```

### 3.4. Running the Local Server

Run the backend server from the `storyteller-api` directory:
`uvicorn app.main:app --reload`

---

## 5. Phase 2: AI & Database Integration (Backend)

### 4.1. AI Service Logic

Update `app/services.py`. This version uses direct HTTP requests, mirroring the `data_monolith` pattern, and includes logic for uploading to Google Cloud Storage.

```python
# app/services.py
import os
import requests
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
GCS_BUCKET_NAME = "storyteller-audio-bucket" # Replace with your actual bucket name

def generate_story_text(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    
    # Simplified single-call generation for MVP
    full_prompt = f"Write a complete, 30-minute sleep story about: {prompt}. The story should be calm, soothing, and descriptive."
    
    json_data = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
    }

    try:
        response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
        response.raise_for_status()
        # Extract text from response
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to call Gemini API: {e}")

def convert_text_to_audio(text: str) -> str:
    # This function would use Google's TTS library.
    # For the MVP, we will assume this step is complex and return a placeholder.
    # A full implementation requires saving the audio and uploading it.
    # The upload_to_gcs function below shows how that would work.
    return "https://storage.googleapis.com/storyteller-audio-bucket/placeholder.mp3"

def upload_to_gcs(file_path: str, destination_blob_name: str) -> str:
    """Uploads a file to the GCS bucket and makes it public."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(file_path)
    blob.make_public()

    return blob.public_url
```

---

## 6. Phase 2.5: Story Generation Validation

### 6.1. Objective
Ensure the iterative, summary-driven story generation process produces a coherent, high-quality story that is appropriate for the target age group (8-12).

### 6.2. Steps
1.  **Execute Test Script:** Run the `test_gemini.py` script locally to generate a full story.
2.  **Review Output:** Read the final story output in the console.
3.  **Validate:** Confirm that the story is well-written, follows the outline, maintains narrative cohesion, and is suitable for children aged 8-12.

### 6.3. Validation Results
- **Status:** Complete and Successful.
- **Word Count:** 2134 words.
- **Estimated Reading Time:** 17-21 minutes at a sleep story pace (100-120 wpm).
- **Next Steps:** The current length is a good baseline. Post-MVP, we will test generating longer stories by increasing the number of points in the outline (e.g., to 7 or 8 points) to reach the 30-minute target.

---

## 7. Phase 3: Frontend Setup (Swift/SwiftUI)

### 5.1. Whisper Integration (`whisper.cpp`)

1.  **Clone Repo:** `git clone https://github.com/ggerganov/whisper.cpp.git`
2.  **Add Files:** Drag the `whisper.h` and `whisper.cpp` files into your Xcode project.
3.  **Bridging Header:** Create a file named `Bridging-Header.h` and add `#include "whisper.h"`. In your project's Build Settings, set the "Objective-C Bridging Header" path to this file.
4.  **Add Model:** Download a Whisper model (e.g., `ggml-base.en.bin`) and add it to your app's bundle.
5.  **Swift Wrapper:** Create a Swift class to manage interaction with the Whisper C++ functions.

### 5.2. Info.plist Configuration

For local development, add the following to your `Info.plist` to allow HTTP connections to your local server:
```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>localhost</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
</dict>
```

---

## 8. Phase 4: Frontend-Backend Integration

### 6.1. Networking Layer

Update `NetworkingService.swift` to use the correct local URL.

```swift
// NetworkingService.swift
import Foundation

class NetworkingService {
    // Use http://localhost:8000 for simulator
    let backendURL = "http://localhost:8000/stories"

    func createStory(prompt: String, completion: @escaping (Result<URL, Error>) -> Void) {
        guard let url = URL(string: backendURL) else { return }
        // ... (rest of the implementation is the same)
    }
}
```

---

## 9. Phase 5: Deployment (Render)

### 7.1. Backend Deployment

1.  **Push to GitHub:** Ensure your `storyteller-api` code is in a public or private GitHub repository.
2.  **Create Render Account:** Sign up for a free account at [render.com](https://render.com).
3.  **New Web Service:**
    *   Click "New" -> "Web Service".
    *   Connect your GitHub account and select the `storyteller` repository.
    *   **Name:** `storyteller-api`
    *   **Root Directory:** `storyteller-api` (This is important, as it tells Render where to find the `requirements.txt` file)
    *   **Runtime:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4.  **Add Environment Variables:** In the "Environment" tab, add your `GEMINI_API_KEY`.
5.  **Deploy:** Click "Create Web Service". Render will build and deploy the application. Use the provided `.onrender.com` URL in your production Swift app.
