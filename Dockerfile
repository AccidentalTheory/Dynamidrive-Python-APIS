# Start with an official Python image (e.g., Python 3.9)
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir reduces image size
# Consider increasing timeout if ML packages take long to install
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy your application code (main.py and any other files) into the container
COPY . .

# --- MODEL HANDLING (Placeholder) ---
# For actual models, you'd need to:
# 1. Add model files to your repo (e.g., in a 'models/' directory) and COPY them here.
#    Example: COPY models/ ./models/
# 2. Or, add commands to download models during the build (can significantly increase build time).
#    Example: RUN python -m my_model_downloader_script
# Your main.py would then load models from the specified path.

# Expose the port the app runs on. FastAPI/Uvicorn default is 8000.
# Fly.io will map its external port (80/443) to this internal port via fly.toml.
EXPOSE 8000

# Command to run the Uvicorn server when the container starts.
# It needs to listen on 0.0.0.0 to be accessible from outside the container (within Fly.io's network).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
