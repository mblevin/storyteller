import requests
import json
import time

def run_live_test():
    """
    Sends a request to the live Render application and logs the process.
    """
    # URL of the running FastAPI application
    API_URL = "https://storyteller-api.onrender.com/stories"

    # The prompt for the story
    prompt_data = {
        "prompt": "A story about a curious robot who explores a futuristic city."
    }

    print("--- [TEST-LOG] Starting live API test. ---")
    try:
        print(f"--- [TEST-LOG] Sending POST request to: {API_URL} ---")
        print(f"--- [TEST-LOG] Request body: {json.dumps(prompt_data, indent=2)} ---")
        
        # Send the POST request with a timeout
        response = requests.post(API_URL, json=prompt_data, timeout=300)
        
        print(f"--- [TEST-LOG] Received response with status code: {response.status_code} ---")
        
        # Raise an exception if the request was unsuccessful
        response.raise_for_status()
        
        # Parse the JSON response
        response_data = response.json()
        
        # Print the results
        print("\n--- [TEST-LOG] Story Generation Successful ---")
        print(f"--- [TEST-LOG] Audio URL: {response_data.get('audio_url')}")
        print("\n--- [TEST-LOG] Story Text ---")
        print(response_data.get('story_text'))
        
    except requests.exceptions.Timeout:
        print("!!! [TEST-ERROR] The request timed out after 5 minutes. !!!")
    except requests.exceptions.RequestException as e:
        print(f"!!! [TEST-ERROR] An error occurred: {e}")
    except json.JSONDecodeError:
        print("!!! [TEST-ERROR] Failed to decode JSON response.")
        print(f"--- [TEST-LOG] Raw Response Text: ---\n{response.text}")
    finally:
        print("\n--- [TEST-LOG] Live API test finished. ---")

if __name__ == "__main__":
    run_live_test()
