from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import os
import shutil
import uuid
import logging
from contextlib import asynccontextmanager

# --- Configuration & Logging ---
TEMP_STORAGE_PATH = "/app/temp_files"  # Directory for temporary file storage
# Ensure this path matches where your Fly app's public URL will point for downloads
# For simplicity, we'll serve files directly. For production, consider signed URLs from cloud storage.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Model Loading (Placeholder) ---
# In a real application, you would load your ML models here.
# This can be time-consuming, so it's often done at application startup.
# Example:
# uvr_model = None
# bs_roformer_model = None

# def load_models():
#     global uvr_model, bs_roformer_model
#     logger.info("Attempting to load ML models...")
#     try:
#         # Replace with your actual model loading logic
#         # uvr_model = YourUVRModelLoader("path/to/uvr_model.onnx")
#         # bs_roformer_model = YourBSRoFormerLoader("path/to/bs_roformer_model.pth")
#         logger.info("ML Models would be loaded here if implemented.")
#     except Exception as e:
#         logger.error(f"Failed to load models: {e}")
#         # Decide if the app should fail to start or run with degraded functionality

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info(f"Temporary storage path: {TEMP_STORAGE_PATH}")
    os.makedirs(TEMP_STORAGE_PATH, exist_ok=True)
    # load_models() # Uncomment to load models on startup
    logger.info("Application startup complete.")
    yield
    # Code to run on shutdown
    logger.info("Cleaning up temporary files...")
    # Basic cleanup: remove the entire temp_files directory on shutdown.
    # For a more robust solution, you might want to clean up older files periodically.
    if os.path.exists(TEMP_STORAGE_PATH):
        shutil.rmtree(TEMP_STORAGE_PATH)
        logger.info(f"Removed temporary storage directory: {TEMP_STORAGE_PATH}")
    logger.info("Application shutdown complete.")


app = FastAPI(lifespan=lifespan)

# --- Helper Functions ---
async def save_upload_file_to_job_dir(upload_file: UploadFile, job_dir: str) -> str:
    """Saves an uploaded file to a specific job directory."""
    try:
        # Sanitize filename (basic example)
        filename = os.path.basename(upload_file.filename or "default_audio.tmp")
        # Prevent path traversal attacks by ensuring filename is just a name
        if ".." in filename or "/" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename.")

        file_path = os.path.join(job_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        logger.info(f"File '{filename}' saved to '{file_path}'")
        return file_path
    except Exception as e:
        logger.error(f"Error saving file {upload_file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {e}")
    finally:
        await upload_file.close()


def generate_dummy_output_files(job_dir: str, api_type: str, original_filename: str):
    """
    Placeholder function to simulate audio separation.
    In a real app, this would call your ML model inference code.
    """
    output_filenames = {}
    base_name, _ = os.path.splitext(original_filename)

    if api_type == "uvr":
        stems = ["vocals", "instrumental"]
    elif api_type == "bsroformer":
        stems = ["vocals", "drums", "bass", "other"]
    else:
        return {}

    for stem in stems:
        # Create dummy .wav files for demonstration
        # In a real scenario, these would be the output of your models
        dummy_filename = f"{base_name}_{stem}.wav"
        dummy_filepath = os.path.join(job_dir, dummy_filename)
        with open(dummy_filepath, "w") as f:
            f.write(f"This is a dummy '{stem}' track for {original_filename} processed by {api_type}.")
        output_filenames[stem] = dummy_filename
        logger.info(f"Generated dummy file: {dummy_filepath}")
    return output_filenames

# --- API Endpoints ---
@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    logger.info("Root endpoint accessed.")
    return {"message": "Audio Separation API is running. Use /separate/{api_type} to process files."}

@app.post("/separate/{api_type}")
async def separate_audio(request: Request, api_type: str, file: UploadFile = File(...)):
    """
    Endpoint to upload an audio file and initiate separation.
    api_type can be 'uvr' or 'bsroformer'.
    """
    logger.info(f"Received separation request for API type: {api_type}, file: {file.filename}")

    if api_type not in ["uvr", "bsroformer"]:
        logger.warning(f"Invalid API type requested: {api_type}")
        raise HTTPException(status_code=400, detail="Invalid API type. Choose 'uvr' or 'bsroformer'.")

    if not file.filename:
        logger.warning("File upload attempted with no filename.")
        raise HTTPException(status_code=400, detail="No filename provided with the upload.")

    # Create a unique directory for this processing job
    request_id = str(uuid.uuid4())
    job_dir = os.path.join(TEMP_STORAGE_PATH, request_id)
    os.makedirs(job_dir, exist_ok=True)
    logger.info(f"Created job directory: {job_dir} for request ID: {request_id}")

    input_audio_path = ""
    try:
        input_audio_path = await save_upload_file_to_job_dir(file, job_dir)

        # --- Actual Model Inference Would Happen Here ---
        logger.info(f"Simulating '{api_type}' processing for: {input_audio_path}")
        # Example:
        # if api_type == "uvr":
        #     output_filenames = uvr_model.separate(input_audio_path, job_dir)
        # elif api_type == "bsroformer":
        #     output_filenames = bs_roformer_model.separate(input_audio_path, job_dir)
        # For now, we use a placeholder:
        output_filenames = generate_dummy_output_files(job_dir, api_type, os.path.basename(input_audio_path))
        # --- End Model Inference Placeholder ---

        if not output_filenames:
            logger.error(f"Processing failed to generate output files for {api_type}.")
            raise HTTPException(status_code=500, detail="Processing stub failed to generate output files.")

        # Construct full URLs for downloading the processed files
        # The base URL needs to be the public URL of your Fly app
        # For simplicity, we are returning relative paths that the /download endpoint will handle.
        # The iOS app will need to prepend the Fly app's base URL.
        output_file_urls = {}
        for stem_name, filename in output_filenames.items():
            # This path is relative to the API root, handled by the /download endpoint
            output_file_urls[stem_name] = f"/download/{request_id}/{filename}"

        logger.info(f"Processing complete for request {request_id}. Output URLs: {output_file_urls}")
        return JSONResponse(content={
            "message": f"'{api_type}' separation (stub) complete for '{file.filename}'.",
            "request_id": request_id,
            "input_file": file.filename,
            "output_urls": output_file_urls # These are relative paths for the /download endpoint
        })

    except HTTPException:
        # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during separation for request {request_id}: {e}", exc_info=True)
        # Clean up job_dir on error if it was created
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
            logger.info(f"Cleaned up job directory {job_dir} due to error.")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@app.get("/download/{request_id}/{filename}")
async def download_separated_file(request_id: str, filename: str):
    """
    Endpoint to download a processed audio file.
    """
    logger.info(f"Download request for file: {filename}, request ID: {request_id}")

    # Basic sanitization
    if ".." in request_id or "/" in request_id or ".." in filename or "/" in filename:
        logger.warning(f"Invalid characters in download path: {request_id}/{filename}")
        raise HTTPException(status_code=400, detail="Invalid file path.")

    file_path = os.path.join(TEMP_STORAGE_PATH, request_id, filename)

    if os.path.isfile(file_path):
        logger.info(f"Serving file: {file_path}")
        # media_type should ideally be specific (e.g., 'audio/wav', 'audio/mpeg')
        # For dummy files, 'text/plain' might be more accurate, but for real audio, use 'audio/*'
        return FileResponse(path=file_path, media_type='audio/wav', filename=filename) # Assume WAV for now
    else:
        logger.warning(f"File not found for download: {file_path}")
        raise HTTPException(status_code=404, detail="File not found. It may have been cleaned up or never existed.")

