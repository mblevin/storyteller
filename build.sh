#!/usr/bin/env bash
# exit on error
set -o errexit

# Print the location of ffmpeg
# This is for debugging purposes, to confirm that ffmpeg is in the path.
which ffmpeg

# Install Python dependencies
pip install -r storyteller-api/requirements.txt
