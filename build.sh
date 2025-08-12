#!/usr/bin/env bash
# exit on error
set -o errexit

# Install ffmpeg
apt-get update && apt-get install -y ffmpeg

# Print the location of ffmpeg
which ffmpeg

# Install Python dependencies
pip install -r storyteller-api/requirements.txt
