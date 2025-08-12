# How to Make a Sample Call to the Storyteller API

To test the story generation functionality, you need to send an HTTP POST request to the `/stories` endpoint of the deployed application.

You can do this using any HTTP client, such as `curl` from your terminal.

### Command

Execute the following command in your terminal:

```bash
curl -X POST "https://storyteller-api-xvdd.onrender.com/stories" \
-H "Content-Type: application/json" \
-d '{
  "prompt": "A story about a knight who is afraid of the dark."
}'
```

### Breakdown of the Command

*   `curl -X POST`: This specifies that you are making a POST request.
*   `"https://storyteller-api-xvdd.onrender.com/stories"`: This is the URL of the live application's endpoint.
*   `-H "Content-Type: application/json"`: This header tells the server that you are sending data in JSON format.
*   `-d '{ "prompt": "..." }'`: This is the body of your request. It is a JSON object with a single key, `"prompt"`, whose value is the story idea you want to generate.

### Expected Response

If the request is successful, the server will respond with a JSON object containing the generated story and the URL for the audio file. It will look like this:

```json
{
  "story_text": "Once upon a time, in a land of towering castles...",
  "audio_url": "https://storage.googleapis.com/storyteller-audio-bucket-mblevin/story-some-unique-id.mp3"
}
```

If the server encounters an error, it will return an error message, which you can view in the Render logs for detailed information.
