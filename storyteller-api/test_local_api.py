import subprocess
import os
import time
import requests
import json
import threading
import sys

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/stories"
HOST = "127.0.0.1"
PORT = 8000
PROMPT_DATA = {
    "prompt": "A short story about a cat who discovers a hidden garden in his backyard."
}

def stream_output(pipe, prefix):
    """Reads and prints output from a subprocess pipe in real-time."""
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line.strip()}", file=sys.stdout, flush=True)
    pipe.close()

def run_test():
    """
    Starts the FastAPI server, sends a request to it, and logs the entire process in real-time.
    """
    server_process = None
    try:
        # 1. Start the Uvicorn server process
        uvicorn_command = [
            "uvicorn",
            "app.main:app",
            f"--host={HOST}",
            f"--port={PORT}"
        ]
        print(f"--- Starting server with command: {' '.join(uvicorn_command)} ---", flush=True)
        
        server_process = subprocess.Popen(
            uvicorn_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"--- Server process started with PID: {server_process.pid} ---", flush=True)

        # Start threads to stream stdout and stderr
        stdout_thread = threading.Thread(target=stream_output, args=(server_process.stdout, "SERVER-STDOUT"))
        stderr_thread = threading.Thread(target=stream_output, args=(server_process.stderr, "SERVER-STDERR"))
        stdout_thread.start()
        stderr_thread.start()

        # 2. Wait for the server to initialize
        print("--- Waiting 15 seconds for server to start... ---", flush=True)
        time.sleep(15)

        # 3. Send the POST request to the API
        print(f"--- Sending POST request to {API_URL} ---", flush=True)
        print(f"--- Request body: {json.dumps(PROMPT_DATA, indent=2)} ---", flush=True)
        
        try:
            response = requests.post(API_URL, json=PROMPT_DATA, timeout=300)
            
            print(f"--- Received response with status code: {response.status_code} ---", flush=True)
            response.raise_for_status()
            
            response_data = response.json()
            print("--- API Response (JSON): ---", flush=True)
            print(json.dumps(response_data, indent=2), flush=True)

        except requests.exceptions.RequestException as e:
            print(f"!!! An error occurred during the request: {e}", flush=True)
        except json.JSONDecodeError:
            print("!!! Failed to decode JSON from response.", flush=True)
            print(f"--- Raw Response Text: ---\n{response.text}", flush=True)

    finally:
        # 4. Shutdown the server
        if server_process:
            print(f"--- Shutting down server (PID: {server_process.pid}) ---", flush=True)
            server_process.terminate()
            
            # Wait for the streaming threads to finish
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            # Ensure the process is terminated
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("!!! Server did not terminate gracefully. Forcing kill. !!!", flush=True)
                server_process.kill()
            
            print("--- Test finished. ---", flush=True)

if __name__ == "__main__":
    run_test()
