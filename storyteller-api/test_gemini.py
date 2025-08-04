import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

def generate_story_text(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    
    # 1. Call Gemini 2.5 Pro to generate a story outline from the prompt.
    outline_prompt = f"Create a 5-point story outline for a 30-minute sleep story about: {prompt}"
    
    json_data = {
        "contents": [{"parts": [{"text": outline_prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "outline": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        }
                    }
                }
            }
        }
    }

    try:
        print("--- Generating Outline ---")
        response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
        print("Full API Response:")
        print(response.json())
        response.raise_for_status()
        outline_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        # The response is a JSON string, so we need to parse it
        import json
        outline_data = json.loads(outline_text)
        story_points = outline_data.get("outline", [])
        outline = "\n".join(story_points)
        print("Outline Received:")
        print(outline)
        print("--------------------------\n")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to call Gemini API for outline: {e}")

    # 2. Loop through each outline point, generating that section of the story.
    full_story = ""
    summary_of_previous_sections = "The story has not yet begun."
    
    for i, point in enumerate(story_points):
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
                print(f"--- Generating Summary for Section {i+1} ---")
                summary_response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=summary_json_data)
                summary_response.raise_for_status()
                summary_of_previous_sections = summary_response.json()["candidates"][0]["content"]["parts"][0]["text"]
                print("Summary Received.")
                print("-------------------------------------\n")
            except requests.exceptions.RequestException as e:
                print(f"Could not generate summary: {e}")
                summary_of_previous_sections = "No summary available."


        section_prompt = f"""
        You are writing a section of a 30-minute sleep story.

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
            print(f"--- Generating Section {i+1}: {point} ---")
            response = requests.post(GEMINI_API_URL, params=params, headers=headers, json=json_data)
            response.raise_for_status()
            section_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            print(f"Section {i+1} Received.")
            full_story += section_text + "\n\n"
            print("----------------------------------\n")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to call Gemini API for section '{point}': {e}")
            
    return full_story

if __name__ == "__main__":
    story = generate_story_text("A story about a friendly dragon")
    print("\n--- Final Story ---")
    print(story)
    print("-------------------")
