# Local End-to-End Test Plan

## Objective
Create and run a Python script to test the FastAPI application locally. The script will start the server, send a request, and log the entire process to verify story and audio generation.

## Prerequisites
1. A `storyteller-api/.env` file must exist and contain the `GEMINI_API_KEY`.
2. The `GOOGLE_APPLICATION_CREDENTIALS` environment variable must be set and point to a valid GCP credentials JSON file.
3. All dependencies from `storyteller-api/requirements.txt` must be installed in the Python environment.

## Steps

### 1. Create the Test Script File
- Create a new file named `test_local_api.py` inside the `storyteller-api/` directory.

### 2. Write the Python Code for `test_local_api.py`

The script will contain the following components:

- **Imports**:
  - `subprocess`: To run the `uvicorn` server process.
  - `os`: To manage environment variables.
  - `time`: To add delays.
  - `requests`: To send the HTTP request.
  - `json`: To handle JSON data.

- **Configuration**:
  - Define constants for the API URL (`http://127.0.0.1:8000/stories`), the host (`127.0.0.1`), and the port (`8000`).
  - Define the `prompt_data` dictionary for the request body.

- **Main Execution Block (`if __name__ == "__main__":`)**:
  - **Start Server**:
    - Define the `uvicorn` command: `["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]`.
    - Use `subprocess.Popen` to start the server. The `stdout` and `stderr` should be redirected to `subprocess.PIPE` to capture logs.
    - Log that the server process has started and print its process ID (PID).
  - **Wait for Server**:
    - Use `time.sleep(15)` to allow the server to initialize completely.
  - **Send Request**:
    - Log that the script is sending a POST request to the API URL.
    - Use a `try...except` block to handle the request.
    - Inside the `try` block:
      - Call `requests.post()` with the URL and JSON data.
      - Set a timeout for the request (e.g., 300 seconds) to handle long-running generation tasks.
      - Log the HTTP status code of the response.
      - Raise an exception for bad status codes using `response.raise_for_status()`.
      - Parse the JSON response using `response.json()`.
      - Log the full content of the JSON response.
    - Inside the `except` block:
      - Log any `requests.exceptions.RequestException` that occurs.
      - Log any `json.JSONDecodeError` that occurs, including the raw response text.
  - **Shutdown Server**:
    - Use a `finally` block to ensure the server is always terminated.
    - Log that the script is shutting down the server.
    - Use `server_process.terminate()` to stop the `uvicorn` process.
    - Use `server_process.wait()` to wait for the process to exit.
    - Log the server's captured `stdout` and `stderr` output.

### 3. Execute the Test
- Open a terminal.
- Navigate to the `storyteller-api/` directory.
- Run the script using the command: `python test_local_api.py`.
- Observe the console output for logs from the script and the server.
