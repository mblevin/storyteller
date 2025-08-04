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
