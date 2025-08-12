import os
import requests
import json
import random
from sqlalchemy.orm import Session
from google.cloud import storage
from . import models, crud, database
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GCS_BUCKET_NAME = "storyteller-audio-bucket-mblevin"

def generate_story_and_audio(story_id: int, prompt: str):
    """
    The background task that generates the story, converts it to audio,
    and updates the database.
    """
    db = database.SessionLocal()
    try:
        crud.update_story_status(db, story_id, "generating_story")
        story_text = generate_story_text(prompt)
        
        crud.update_story_status(db, story_id, "generating_audio")
        audio_url = convert_text_to_audio(story_text)
        
        crud.complete_story(db, story_id, story_text, audio_url)
        
    except Exception as e:
        print(f"!!! [ERROR] Background task failed for story {story_id}: {e}")
        crud.update_story_status(db, story_id, "failed")
    finally:
        db.close()

def generate_story_text(prompt: str) -> str:
    print("--- [LOG] Starting story generation process. ---")
    
    # 1. Call Gemini 2.5 Pro to generate a story outline from the prompt.
    print("--- [LOG] Generating story outline. ---")
    outline_prompt = f"""
    Create a 15-point story outline for a 30-minute sleep story about: {prompt}.
    The story should be appropriate for a child aged 8-12.
    The outline should follow a "gradual unwind" structure, starting in a calm and peaceful setting and becoming progressively more relaxing and dreamlike.
    The outline should include mindfulness elements, such as focusing on the breath and sensory details.

    **IMPORTANT:** Format the output as a JSON object with a single key "outline" which is an array of strings.
    Example: {{"outline": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5", "Point 6", "Point 7", "Point 8", "Point 9", "Point 10", "Point 11", "Point 12", "Point 13", "Point 14", "Point 15"]}}
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        print("--- [LOG] Sending request to Gemini for outline. ---")
        response = model.generate_content(
            outline_prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        print("--- [LOG] Received response from Gemini for outline. ---")
        
        outline_data = json.loads(response.text)
        story_points = outline_data.get("outline", [])
        outline = "\n".join(story_points)
        print(f"--- [LOG] Successfully parsed outline with {len(story_points)} points. ---")

    except Exception as e:
        print(f"!!! [ERROR] Failed to call Gemini API for outline: {e}")
        raise RuntimeError(f"Failed to call Gemini API for outline: {e}")

    # 2. Loop through each outline point, generating that section of the story.
    full_story = ""
    summary_of_previous_sections = "The story has not yet begun."
    
    print("--- [LOG] Starting to generate story sections. ---")
    for i, point in enumerate(story_points):
        print(f"--- [LOG] Generating section {i+1}/{len(story_points)}: '{point}' ---")
        # Generate an interim summary if we have some story text
        if full_story:
            print(f"--- [LOG] Generating summary for section {i+1}. ---")
            summarization_prompt = f"""
            Based on the story written so far, provide a brief summary. Include the main characters, their current situation, and the key events that have occurred.

            **Story So Far:**
            {full_story}
            """
            try:
                print(f"--- [LOG] Sending request to Gemini for summary. ---")
                summary_response = model.generate_content(
                    summarization_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.5,
                        max_output_tokens=512
                    )
                )
                summary_of_previous_sections = summary_response.text
                print(f"--- [LOG] Successfully generated summary for section {i+1}. ---")
            except Exception as e:
                print(f"!!! [ERROR] Could not generate summary: {e}")
                summary_of_previous_sections = "No summary available."

        section_prompt = f"""
        You are a master storyteller, crafting a section of a 30-minute sleep story for a child aged 8-12. Your writing should be calm, soothing, and poetic.

        **Style Guidelines:**
        *   **Lush, Descriptive Language:** Use rich, sensory language that appeals to all the senses (sight, sound, smell, touch, taste).
        *   **Focus on the Present Moment:** Describe the character's experience as if it is happening right now.
        *   **Avoid Conflict and Tension:** The story should be completely free of conflict, tension, or any startling events. The tone should be one of peace and tranquility.
        *   **Gradual Unwind:** Each section should become progressively more relaxing and dreamlike.

        **Original User Request:** {prompt}

        **Full Story Outline:**
        {outline}

        **Summary of Previous Sections:**
        {summary_of_previous_sections}

        **The last paragraph of the previous section was:**
        ...{full_story[-500:]}

        **Now, please write the next section of the story, focusing on this point from the outline:** '{point}'
        """
        
        try:
            print(f"--- [LOG] Sending request to Gemini for story section {i+1}. ---")
            response = model.generate_content(
                section_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=models.StorySection
                )
            )
            print(f"--- [LOG] Received response from Gemini for story section {i+1}. ---")
            
            section_data = json.loads(response.text)
            section_text = section_data.get("story_section_text", "")
            full_story += section_text + "\n\n[pause long]\n\n"
            print(f"--- [LOG] Successfully generated and appended section {i+1}. ---")

        except Exception as e:
            print(f"!!! [ERROR] Failed to call Gemini API for section '{point}': {e}")
            raise RuntimeError(f"Failed to call Gemini API for section '{point}': {e}")
        except json.JSONDecodeError:
            print(f"!!! [ERROR] Error decoding JSON for section {i+1}. Response text: {response.text}")

            
    return full_story

def convert_text_to_audio(text: str) -> str:
    """Converts text to an audio file using the Long Audio Synthesis API."""
    print("--- [LOG] Starting Long Audio Synthesis process. ---")
    try:
        from google.cloud import texttospeech_v1beta1 as texttospeech
        from google.oauth2 import service_account
        import uuid

        gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not gcp_credentials_path:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not set.")

        credentials = service_account.Credentials.from_service_account_file(gcp_credentials_path)
        client = texttospeech.TextToSpeechLongAudioSynthesizeClient(credentials=credentials)

        input_text = texttospeech.SynthesisInput(text=text)

        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        voices = [
            "en-US-Chirp3-HD-Achernar",
            "en-US-Chirp3-HD-Gacrux",
            "en-US-Chirp3-HD-Leda",
            "en-US-Chirp3-HD-Sulafat",
        ]
        random_voice = random.choice(voices)

        voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=random_voice)
        
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise RuntimeError("GCP_PROJECT_ID not set.")

        parent = f"projects/{project_id}/locations/us-central1"
        
        destination_blob_name = f"story-{uuid.uuid4()}.mp3"
        output_gcs_uri = f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"

        request = texttospeech.SynthesizeLongAudioRequest(
            parent=parent,
            input=input_text,
            audio_config=audio_config,
            voice=voice,
            output_gcs_uri=output_gcs_uri,
        )

        print("--- [LOG] Submitting Long Audio Synthesis request. ---")
        operation = client.synthesize_long_audio(request=request)
        
        print("--- [LOG] Waiting for Long Audio Synthesis operation to complete... ---")
        result = operation.result(timeout=600)  # 10-minute timeout
        print("--- [LOG] Long Audio Synthesis operation complete. ---")

        # The public URL needs to be constructed manually
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{destination_blob_name}"
        
        # Make the object public
        storage_client = storage.Client(credentials=credentials)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.make_public()
        print(f"--- [LOG] Made GCS object public at: {public_url} ---")

        return public_url

    except Exception as e:
        print(f"!!! [ERROR] An error occurred during Long Audio Synthesis: {e}")
        raise RuntimeError(f"TTS Error: {e}")

def upload_to_gcs(file_path: str, destination_blob_name: str) -> str:
    """Uploads a file to the GCS bucket and makes it public."""
    print(f"--- [LOG] Initializing GCS client for bucket: {GCS_BUCKET_NAME}. ---")
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    print(f"--- [LOG] Starting upload of '{file_path}' to '{destination_blob_name}'. ---")
    blob.upload_from_filename(file_path)
    print(f"--- [LOG] Finished uploading to GCS. ---")

    return blob.public_url
