import os
from google.cloud import texttospeech
from google.oauth2 import service_account

# Load the credentials from the environment variable
gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not gcp_credentials_path:
    raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

credentials = service_account.Credentials.from_service_account_file(gcp_credentials_path)
client = texttospeech.TextToSpeechClient(credentials=credentials)

# Set up the synthesis request
synthesis_input = texttospeech.SynthesisInput(text="Hello, world!")

voice = texttospeech.VoiceSelectionParams(
    language_code="en-US", name="en-US-Chirp3-HD-Achernar"
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Make the request
try:
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # The response's audio_content is binary.
    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')

except Exception as e:
    print(f"An error occurred: {e}")
