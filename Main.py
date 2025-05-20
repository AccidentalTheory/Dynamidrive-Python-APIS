from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import os
import shutil
import uuid
import logging
from contextlib import asynccontextmanager

# --- Configuration & Logging ---
TEMP_STORAGE_PATH = "/app/temp_files"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Application startup: Initializing temporary storage at {TEMP_STORAGE_PATH}")
    os.makedirs(TEMP_STORAGE_PATH, exist_ok=True)
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown: Starting cleanup of temporary files...")
    if os.path.exists(TEMP_STORAGE_PATH):
        try:
            shutil.rmtree(TEMP_STORAGE_PATH)
            logger.info(f"Successfully removed temporary storage directory: {TEMP_STORAGE_PATH}")
        except Exception as e:
            logger.error(f"Error during cleanup of temporary storage directory {TEMP_STORAGE_PATH}: {e}", exc_info=True)
    logger.info("Application shutdown complete.")


app = FastAPI(lifespan=lifespan)

# --- Helper Functions ---
async def save_upload_file_to_job_dir(upload_file: UploadFile, job_dir: str) -> str:
    """Saves an uploaded file to a specific job directory."""
    original_filename = upload_file.filename or "default_audio.tmp"
    # Basic sanitization for filename
    filename = os.path.basename(original_filename)
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        logger.error(f"Invalid filename received: {original_filename}")
        raise HTTPException(status_code=400, detail=f"Invalid filename: {original_filename}")

    file_path = os.path.join(job_dir, filename)
    logger.info(f"Attempting to save uploaded file '{original_filename}' to '{file_path}'")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        logger.info(f"Successfully saved file '{original_filename}' to '{file_path}', size: {os.path.getsize(file_path)} bytes")
        return file_path
    except Exception as e:
        logger.error(f"Error saving uploaded file {original_filename} to {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file '{original_filename}': {str(e)}")
    finally:
        await upload_file.close()
        logger.info(f"Closed uploaded file object for '{original_filename}'")


def generate_dummy_output_files(job_dir: str, api_type: str, original_filename: str):
    """Placeholder function to simulate audio separation."""
    output_filenames = {}
    base_name, ext = os.path.splitext(original_filename)
    if not base_name: # Handle cases like ".mp3" if basename becomes empty
        base_name = "output"

    logger.info(f"Generating dummy output files for api_type: {api_type}, original_filename: {original_filename}, base_name: {base_name}")

    if api_type == "uvr":
        stems = ["vocals", "instrumental"]
    elif api_type == "bsroformer":
        stems = ["vocals", "drums", "bass", "other"]
    else:
        logger.warning(f"Unknown api_type '{api_type}' in generate_dummy_output_files.")
        return {}

    for stem in stems:
        dummy_filename = f"{base_name}_{stem}.wav" # Still creating .wav for consistency with API contract
        dummy_filepath = os.path.join(job_dir, dummy_filename)
        try:
            with open(dummy_filepath, "w") as f: # Writing text content to a .wav named file
                f.write(f"This is a dummy '{stem}' track for {original_filename} processed by {api_type}.")
            output_filenames[stem] = dummy_filename
            logger.info(f"Generated dummy file: {dummy_filepath}")
        except Exception as e:
            logger.error(f"Failed to generate dummy file {dummy_filepath}: {e}", exc_info=True)
            # Decide if one failed dummy file should stop the whole process or just be skipped
    return output_filenames

# --- API Endpoints ---
@app.get("/")
async def root():
    logger.info("Root endpoint '/' accessed.")
    return {"message": "Audio Separation API is running. Use /separate/{api_type} to process files."}

@app.post("/separate/{api_type}")
async def separate_audio(request: Request, api_type: str, file: UploadFile = File(...)):
    request_id = str(uuid.uuid4())
    job_dir = os.path.join(TEMP_STORAGE_PATH, request_id)
    
    logger.info(f"Request ID {request_id}: Received separation request for API type: '{api_type}', input filename: '{file.filename}', content-type: '{file.content_type}'")

    if api_type not in ["uvr", "bsroformer"]:
        logger.warning(f"Request ID {request_id}: Invalid API type requested: {api_type}")
        raise HTTPException(status_code=400, detail=f"Invalid API type. Choose 'uvr' or 'bsroformer'. Provided: '{api_type}'")

    if not file.filename:
        logger.warning(f"Request ID {request_id}: File upload attempted with no filename.")
        raise HTTPException(status_code=400, detail="No filename provided with the upload.")

    try:
        os.makedirs(job_dir, exist_ok=True)
        logger.info(f"Request ID {request_id}: Created job directory: {job_dir}")

        input_audio_path = await save_upload_file_to_job_dir(file, job_dir)
        logger.info(f"Request ID {request_id}: Input file saved to '{input_audio_path}'")

        logger.info(f"Request ID {request_id}: Simulating '{api_type}' processing for: {input_audio_path}")
        output_filenames = generate_dummy_output_files(job_dir, api_type, os.path.basename(input_audio_path))
        
        if not output_filenames:
            logger.error(f"Request ID {request_id}: Processing by '{api_type}' failed to generate any output files for '{os.path.basename(input_audio_path)}'.")
            # This case might indicate a logic error in generate_dummy_output_files or an unknown api_type not caught earlier
            raise HTTPException(status_code=500, detail=f"Processing for '{api_type}' generated no output files. This might be an issue with the API type or internal processing logic.")

        output_file_urls = {}
        for stem_name, filename in output_filenames.items():
            output_file_urls[stem_name] = f"/download/{request_id}/{filename}"

        response_payload = {
            "message": f"'{api_type}' separation (stub) complete for '{file.filename}'.",
            "request_id": request_id,
            "input_file": file.filename,
            "output_urls": output_file_urls
        }
        logger.info(f"Request ID {request_id}: Processing complete. Sending JSON response: {response_payload}")
        return JSONResponse(content=response_payload)

    except HTTPException as http_exc:
        logger.error(f"Request ID {request_id}: HTTPException during separation: {http_exc.status_code} - {http_exc.detail}", exc_info=True)
        raise # Re-raise HTTPException to be handled by FastAPI's default error handler (which returns JSON)
    except Exception as e:
        logger.error(f"Request ID {request_id}: An unexpected error occurred during separation: {str(e)}", exc_info=True)
        # Clean up job_dir on unexpected error
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
                logger.info(f"Request ID {request_id}: Cleaned up job directory {job_dir} due to unexpected error.")
            except Exception as cleanup_exc:
                logger.error(f"Request ID {request_id}: Error during cleanup of job directory {job_dir} after another error: {cleanup_exc}", exc_info=True)
        # Return a generic 500 error as JSON
        return JSONResponse(
            status_code=500,
            content={"detail": f"An internal server error occurred. Request ID: {request_id}. Error: {str(e)}"}
        )


@app.get("/download/{request_id}/{filename}")
async def download_separated_file(request_id: str, filename: str):
    logger.info(f"Download request for file: '{filename}', request ID: '{request_id}'")

    # Sanitize request_id and filename to prevent path traversal
    if not request_id.isalnum() or ".." in request_id or "/" in request_id: # Basic check for UUID format
        logger.warning(f"Invalid characters or format in download request_id: '{request_id}'")
        raise HTTPException(status_code=400, detail="Invalid request ID format.")
    
    # Basename again to be sure, though it should be clean from generation
    sane_filename = os.path.basename(filename)
    if sane_filename != filename or ".." in sane_filename or "/" in sane_filename:
        logger.warning(f"Invalid characters or format in download filename: '{filename}' (sanitized to '{sane_filename}')")
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    file_path = os.path.join(TEMP_STORAGE_PATH, request_id, sane_filename)

    if os.path.isfile(file_path):
        logger.info(f"Serving file: {file_path}")
        return FileResponse(path=file_path, media_type='audio/wav', filename=sane_filename) # Assuming WAV for dummy
    else:
        logger.warning(f"File not found for download: {file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: '{sane_filename}'. It may have been cleaned up or the request ID is incorrect.")