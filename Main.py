from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
import os
from audio_separator import Separator

app = FastAPI()
separator = Separator()  # Uses default model (UVR/MDX/BS-RoFormer supported)

UPLOAD_DIR = "/tmp/uploads"
OUTPUT_DIR = "/tmp/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/separate")
async def separate_audio(
    file: UploadFile = File(...),
    model_filename: str = Form(None)  # Optional: specify a model (e.g., BS-RoFormer)
):
    # Save uploaded file
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Prepare output directory for this file
    file_output_dir = os.path.join(OUTPUT_DIR, os.path.splitext(file.filename)[0])
    os.makedirs(file_output_dir, exist_ok=True)

    # Run separation
    try:
        if model_filename:
            separator.separate(
                input_path,
                output_dir=file_output_dir,
                model_filename=model_filename
            )
        else:
            separator.separate(
                input_path,
                output_dir=file_output_dir
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    # List output files
    output_files = [
        os.path.join(file_output_dir, f)
        for f in os.listdir(file_output_dir)
        if os.path.isfile(os.path.join(file_output_dir, f))
    ]

    # Return list of output files (you can also return download links)
    return {"outputs": [os.path.basename(f) for f in output_files]}

@app.get("/download/{filename}")
async def download_file(filename: str):
    # Find the file in OUTPUT_DIR
    for root, dirs, files in os.walk(OUTPUT_DIR):
        if filename in files:
            return FileResponse(os.path.join(root, filename))
    return JSONResponse(status_code=404, content={"error": "File not found"})
