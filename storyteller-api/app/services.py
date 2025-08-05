import os
import requests
import json
from google.cloud import storage

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
GCS_BUCKET_NAME = "storyteller-audio-bucket-mblevin"

def generate_story_text(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    
    # 1. Call Gemini 2.5 Pro to generate a story outline from the prompt.
    outline_prompt = f"""
    Create a 5-point story outline for a 30-minute sleep story about: {prompt}.
    The story should be appropriate for a child aged 8-12.

    **IMPORTANT:** Format the output as a JSON object with a single key "outline" which is an array of strings.
    Example: {{"outline": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]}}
    """
    
    json_data = {
        "contents": [{"parts": [{"text": outline_prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
        }
    }

    try:
        response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
        response.raise_for_status()
        
        # Safely access the generated text
        response_data = response.json()
        print(f"Gemini API response for outline: {json.dumps(response_data, indent=2)}")
        if "candidates" in response_data and response_data["candidates"]:
            content = response_data["candidates"][0].get("content", {})
            if "parts" in content and content["parts"]:
                outline_text = content["parts"][0].get("text", "")
                outline_data = json.loads(outline_text)
                story_points = outline_data.get("outline", [])
                outline = "\n".join(story_points)
            else:
                raise RuntimeError(f"Gemini API response for outline is missing 'parts' key. Response: {response_data}")
        else:
            raise RuntimeError(f"Gemini API response for outline is missing 'candidates' key. Response: {response_data}")

    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
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
            summary_json_data = {
                "contents": [{"parts": [{"text": summarization_prompt}]}],
                "generationConfig": {"temperature": 0.5, "maxOutputTokens": 512}
            }
            try:
                summary_response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=summary_json_data)
                summary_response.raise_for_status()
                summary_of_previous_sections = summary_response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except requests.exceptions.RequestException as e:
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
        
        json_data = {
            "contents": [{"parts": [{"text": section_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
                "response_mime_type": "application/json"
            }
        }
        
        try:
            response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
            response.raise_for_status()
            
            # Safely access the generated text
            response_data = response.json()
            print(f"Gemini API response for section {i+1}: {json.dumps(response_data, indent=2)}")
            if "candidates" in response_data and response_data["candidates"]:
                content = response_data["candidates"][0].get("content", {})
                if "parts" in content and content["parts"]:
                    section_json_text = content["parts"][0].get("text", "")
                    section_data = json.loads(section_json_text)
                    section_text = section_data.get("story_section_text", "")
                    full_story += section_text + "\n\n"
                    print(f"Successfully generated section {i+1}.")
                else:
                    print(f"Warning: 'parts' key missing in response for section {i+1}. Response: {response_data}")
            else:
                print(f"Warning: 'candidates' key missing or empty in response for section {i+1}. Response: {response_data}")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call Gemini API for section '{point}': {e}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON for section {i+1}. Response text: {response.text}")

            
    return full_story

def convert_text_to_audio(text: str) -> str:
    """Converts text to an audio file using Google TTS and returns a public URL."""
    print("--- Starting Text-to-Speech Conversion ---")
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", name="en-US-Wavenet-F"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
    except Exception as e:
        print(f"!!! An error occurred during Text-to-Speech conversion: {e}")
        raise RuntimeError(f"TTS Error: {e}")

    # Save the audio content to a temporary file
    temp_file_path = "/tmp/output.mp3"
    with open(temp_file_path, "wb") as out:
        out.write(response.audio_content)

    # Upload the file to GCS and get the public URL
    # The destination blob name can be generated to be unique, e.g., using a UUID
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
