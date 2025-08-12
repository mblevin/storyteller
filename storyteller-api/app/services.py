import os
import requests
import json
from google.cloud import storage
from . import models
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GCS_BUCKET_NAME = "storyteller-audio-bucket-mblevin"

def generate_story_text(prompt: str) -> str:
    print("--- [LOG] Starting story generation process. ---")
    
    # 1. Call Gemini 2.5 Pro to generate a story outline from the prompt.
    print("--- [LOG] Generating story outline. ---")
    outline_prompt = f"""
    Create a 5-point story outline for a 30-minute sleep story about: {prompt}.
    The story should be appropriate for a child aged 8-12.

    **IMPORTANT:** Format the output as a JSON object with a single key "outline" which is an array of strings.
    Example: {{"outline": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]}}
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
            
            section_text = response.text
            full_story += section_text + "\n\n"
            print(f"--- [LOG] Successfully generated and appended section {i+1}. ---")

        except Exception as e:
            print(f"!!! [ERROR] Failed to call Gemini API for section '{point}': {e}")
            raise RuntimeError(f"Failed to call Gemini API for section '{point}': {e}")
        except json.JSONDecodeError:
            print(f"!!! [ERROR] Error decoding JSON for section {i+1}. Response text: {response.text}")

            
    return full_story

def convert_text_to_audio(text: str) -> str:
    """Converts text to an audio file using Google TTS and returns a public URL."""
    print("--- [LOG] Starting Text-to-Speech conversion process. ---")
    try:
        print("--- [LOG] Importing TTS libraries. ---")
        from google.cloud import texttospeech
        from google.oauth2 import service_account
        from pydub import AudioSegment
        import io

        AudioSegment.converter = "/usr/bin/ffmpeg"

        gcp_credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not gcp_credentials_json:
            print("!!! [ERROR] GOOGLE_APPLICATION_CREDENTIALS environment variable not set. !!!")
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        
        print("--- [LOG] Loading GCP credentials. ---")
        gcp_credentials = json.loads(gcp_credentials_json)
        credentials = service_account.Credentials.from_service_account_info(gcp_credentials)
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        print("--- [LOG] TTS client created successfully. ---")

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", name="en-US-Wavenet-F"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Split the text into chunks of 4500 bytes
        print("--- [LOG] Splitting text into chunks for TTS. ---")
        text_bytes = text.encode('utf-8')
        byte_chunks = [text_bytes[i:i + 4500] for i in range(0, len(text_bytes), 4500)]
        audio_segments = []
        print(f"--- [LOG] Text split into {len(byte_chunks)} chunks. ---")

        for i, chunk in enumerate(byte_chunks):
            print(f"--- [LOG] Synthesizing chunk {i+1}/{len(byte_chunks)}. ---")
            synthesis_input = texttospeech.SynthesisInput(text=chunk.decode('utf-8'))
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            audio_segments.append(AudioSegment.from_mp3(io.BytesIO(response.audio_content)))
            print(f"--- [LOG] Successfully synthesized chunk {i+1}. ---")

        print("--- [LOG] Concatenating audio chunks. ---")
        combined_audio = sum(audio_segments)

        # Save the combined audio to a temporary file
        temp_file_path = "/tmp/output.mp3"
        print(f"--- [LOG] Exporting combined audio to temporary file: {temp_file_path} ---")
        combined_audio.export(temp_file_path, format="mp3")
        print("--- [LOG] Successfully exported audio to temporary file. ---")

    except Exception as e:
        print(f"!!! [ERROR] An error occurred during Text-to-Speech conversion: {e}")
        raise RuntimeError(f"TTS Error: {e}")

    # Upload the file to GCS and get the public URL
    import uuid
    destination_blob_name = f"story-{uuid.uuid4()}.mp3"
    print(f"--- [LOG] Uploading audio file to GCS as '{destination_blob_name}'. ---")
    public_url = upload_to_gcs(temp_file_path, destination_blob_name)
    
    print(f"--- [LOG] Successfully generated audio. Public URL: {public_url} ---")
    return public_url

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
