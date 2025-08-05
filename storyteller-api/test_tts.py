import os
from app.services import convert_text_to_audio

# Set the environment variable to point to the credentials file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "storyteller-api/gcp-credentials.json"

print("--- Starting TTS Test ---")
try:
    # A short text to test the TTS service
    test_text = "Hello, this is a test of the Text-to-Speech service."
    audio_url = convert_text_to_audio(test_text)
    print(f"Successfully generated audio file: {audio_url}")
except Exception as e:
    print(f"An error occurred during the TTS test: {e}")
finally:
    # The user has requested not to clean up the credentials file.
    pass
