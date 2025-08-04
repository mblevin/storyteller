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
    
    # 1. Call Gemini 2.5 Pro to generate a story outline from the prompt.
    outline_prompt = f"Create a 5-point story outline for a 30-minute sleep story about: {prompt}"
    
    json_data = {
        "contents": [{"parts": [{"text": outline_prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }

    try:
        response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
        response.raise_for_status()
        outline = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to call Gemini API for outline: {e}")

    # 2. Loop through each outline point, generating that section of the story.
    full_story = ""
    for point in outline.split('\n'):
        if not point.strip():
            continue
            
        section_prompt = f"Write the '{point}' part of a sleep story about {prompt}. Context of the story so far: {full_story[-500:]}"
        
        json_data = {
            "contents": [{"parts": [{"text": section_prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
        }
        
        try:
            response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
            response.raise_for_status()
            section_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            full_story += section_text + "\n\n"
        except requests.exceptions.RequestException as e:
            # In a real app, you might want to handle this more gracefully
            raise RuntimeError(f"Failed to call Gemini API for section '{point}': {e}")
            
    return full_story

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
