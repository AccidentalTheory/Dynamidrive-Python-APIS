from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
import os
import logging
from audio_separator import Separator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
separator = Separator()  # Uses default model (UVR/MDX-BS-RoFormer supported)
UPLOAD_DIR = "./uploads"
OUTPUT_DIR = "./outputs"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/separate")
async def separate_audio(file: UploadFile = File(...), model_filename: str = Form(None)):
    """
    Separate an audio file into multiple tracks using the specified or default model.
    """
    # Save uploaded file
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    logger.info(f"Saving uploaded file to {input_path}")
    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        logger.error(f"Failed to save file: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Failed to save file: {str(e)}"})

    # Prepare output directory for this file
    file_output_dir = os.path.join(OUTPUT_DIR, os.path.splitext(file.filename)[0])
    os.makedirs(file_output_dir, exist_ok=True)

    # Run separation
    logger.info(f"Starting separation for {file.filename} with model: {model_filename or 'default'}")
    try:
        if model_filename:
            separator.separate(input_path, file_output_dir, model_filename=model_filename)
        else:
            separator.separate(input_path, file_output_dir)
    except Exception as e:
        logger.error(f"Separation failed: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Separation failed: {str(e)}"})

    # Get list of output files (only filenames)
    output_files = [
        f for f in os.listdir(file_output_dir)
        if os.path.isfile(os.path.join(file_output_dir, f))
    ]
    logger.info(f"Separation complete, output files: {output_files}")

    return JSONResponse(status_code=200, content={"output_files": output_files})

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a separated audio file.
    """
    logger.info(f"Request to download file: {filename}")
    for root, dirs, files in os.walk(OUTPUT_DIR):
        if filename in files:
            file_path = os.path.join(root, filename)
            logger.info(f"Found file at {file_path}")
            return FileResponse(file_path)
    logger.error(f"File not found: {filename}")
    return JSONResponse(status_code=404, content={"error": "File not found"})
