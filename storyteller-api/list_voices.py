import os
from google.cloud import texttospeech
from google.oauth2 import service_account

def list_voices():
    """Lists the available voices."""
    try:
        gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not gcp_credentials_path:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

        credentials = service_account.Credentials.from_service_account_file(gcp_credentials_path)
        client = texttospeech.TextToSpeechClient(credentials=credentials)

        # Performs the list voices request
        voices = client.list_voices(language_code="en-US")

        print("Available en-US Voices:")
        for voice in voices.voices:
            print(f"- Name: {voice.name}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    list_voices()
