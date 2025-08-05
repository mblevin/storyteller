import os
import requests
import json
from google.cloud import storage
from . import models
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GCS_BUCKET_NAME = "storyteller-audio-bucket-mblevin"

def generate_story_text(prompt: str) -> str:
    
    # 1. Call Gemini 2.5 Pro to generate a story outline from the prompt.
    outline_prompt = f"""
    Create a 5-point story outline for a 30-minute sleep story about: {prompt}.
    The story should be appropriate for a child aged 8-12.

    **IMPORTANT:** Format the output as a JSON object with a single key "outline" which is an array of strings.
    Example: {{"outline": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]}}
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content(
            outline_prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        outline_data = json.loads(response.text)
        story_points = outline_data.get("outline", [])
        outline = "\n".join(story_points)

    except Exception as e:
        raise RuntimeError(f"Failed to call Gemini API for outline: {e}")

    print(f"Successfully generated story outline with {len(story_points)} points.")

    # 2. Loop through each outline point, generating that section of the story.
    full_story = ""
    summary_of_previous_sections = "The story has not yet begun."
    
    for i, point in enumerate(story_points):
        print(f"--- Generating section {i+1}/{len(story_points)}: '{point}' ---")
        # Generate an interim summary if we have some story text
        if full_story:
            summarization_prompt = f"""
            Based on the story written so far, provide a brief summary. Include the main characters, their current situation, and the key events that have occurred.

            **Story So Far:**
            {full_story}
            """
            try:
                summary_response = model.generate_content(
                    summarization_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.5,
                        max_output_tokens=512
                    )
                )
                summary_of_previous_sections = summary_response.text
            except Exception as e:
                print(f"Could not generate summary: {e}")
                summary_of_previous_sections = "No summary available."

        section_prompt = f"""
        You are writing a section of a 30-minute sleep story for a child aged 8-12.

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
            response = model.generate_content(
                section_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=models.StorySection
                )
            )
            
            section_text = response.text
            full_story += section_text + "\n\n"
            print(f"Successfully generated section {i+1}.")

        except Exception as e:
            raise RuntimeError(f"Failed to call Gemini API for section '{point}': {e}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON for section {i+1}. Response text: {response.text}")

            
    return full_story

def convert_text_to_audio(text: str) -> str:
    """Converts text to an audio file using Google TTS and returns a public URL."""
    print("--- Starting Text-to-Speech Conversion ---")
    try:
        from google.cloud import texttospeech
        from google.oauth2 import service_account
        from pydub import AudioSegment
        import io

        gcp_credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not gcp_credentials_json:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

        gcp_credentials = json.loads(gcp_credentials_json)
        credentials = service_account.Credentials.from_service_account_info(gcp_credentials)
        client = texttospeech.TextToSpeechClient(credentials=credentials)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", name="en-US-Wavenet-F"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Split the text into chunks of 4500 bytes
        text_chunks = [text[i:i + 4500] for i in range(0, len(text), 4500)]
        audio_segments = []

        for i, chunk in enumerate(text_chunks):
            print(f"--- Synthesizing chunk {i+1}/{len(text_chunks)} ---")
            synthesis_input = texttospeech.SynthesisInput(text=chunk)
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            audio_segments.append(AudioSegment.from_mp3(io.BytesIO(response.audio_content)))

        print("--- Concatenating audio chunks ---")
        combined_audio = sum(audio_segments)

        # Save the combined audio to a temporary file
        temp_file_path = "/tmp/output.mp3"
        combined_audio.export(temp_file_path, format="mp3")

    except Exception as e:
        print(f"!!! An error occurred during Text-to-Speech conversion: {e}")
        raise RuntimeError(f"TTS Error: {e}")

    # Upload the file to GCS and get the public URL
    import uuid
    destination_blob_name = f"story-{uuid.uuid4()}.mp3"
    print(f"Uploading audio file to GCS as '{destination_blob_name}'...")
    public_url = upload_to_gcs(temp_file_path, destination_blob_name)
    
    print(f"Successfully generated audio. Public URL: {public_url}")
    return public_url

def upload_to_gcs(file_path: str, destination_blob_name: str) -> str:
    """Uploads a file to the GCS bucket and makes it public."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(file_path)

    return blob.public_url
