FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /apt/lists/*

# Clone the repositories
RUN git clone https://github.com/NextAudioGen/ultimatevocalremover_api.git
RUN git clone https://github.com/nomadkaraoke/python-audio-separator.git

# Install dependencies for both APIs
RUN pip install --no-cache-dir -r ultimatevocalremover_api/requirements.txt
RUN pip install --no-cache-dir -r python-audio-separator/requirements.txt
RUN pip install fastapi uvicorn torch audiofile

# Copy FastAPI server code
COPY server.py .

# Expose port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
