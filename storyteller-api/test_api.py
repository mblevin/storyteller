import requests
import json
import time

# Give the server time to start up
time.sleep(10)

# URL of the running FastAPI application
API_URL = "https://storyteller-api-xvdd.onrender.com/stories"

# The prompt for the story
prompt_data = {
    "prompt": "A story about a friendly dragon who learns to bake"
}

try:
    print(f"Sending request to {API_URL}...")
    # Send the POST request
    response = requests.post(API_URL, json=prompt_data)
    
    # Raise an exception if the request was unsuccessful
    response.raise_for_status()
    
    # Parse the JSON response
    response_data = response.json()
    
    # Print the results
    print("--- Story Generation Successful ---")
    print(f"Audio URL: {response_data.get('audio_url')}")
    print("\n--- Story Text ---")
    print(response_data.get('story_text'))
    
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
except json.JSONDecodeError:
    print("Failed to decode JSON response.")
    print(f"Response text: {response.text}")
