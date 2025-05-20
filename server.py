from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import os
import shutil
from uvr import models as uvr_models
from uvr.utils.get_models import download_all_models
import json
import torch
from audio_separator import Separator
import tempfile

app = FastAPI()

# Initialize UltimateVocalRemover
with open("/app/ultimatevocalremover_api/src/models_dir/models.json", "r") as f:
    models_json = json.load(f)
download_all_models(models_json)
uvr_model = uvr_models.Demucs(name="hdemucs_mmi", other_metadata={"segment": 2, "split": True}, device="cpu")

# Initialize BS-RoFormer
bs_model = Separator(model_filename="model_bs_roformer_ep_317_sdr_12.9755.yaml", device="cpu")

@app.post("/separate/ultimatevocalremover")
async def separate_uvr(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    result = uvr_model(temp_path)
    vocals_path = f"{temp_path}_vocals.wav"
    instrumental_path = f"{temp_path}_instrumental.wav"
    result["vocals"].tofile(vocals_path)
    result["instrumental"].tofile(instrumental_path)

    return {
        "vocals": FileResponse(vocals_path, media_type="audio/wav", filename="vocals.wav"),
        "instrumental": FileResponse(instrumental_path, media_type="audio/wav", filename="instrumental.wav")
    }

@app.post("/separate/bsroformer")
async def separate_bsroformer(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    output_files = bs_model.separate(temp_path)
    vocals_path = next((f for f in output_files if "Vocals" in f), None)
    instrumental_path = next((f for f in output_files if "instrumental" in f), None)

    return {
        "vocals": FileResponse(vocals_path, media_type="audio/wav", filename="vocals.wav") if vocals_path else None,
        "instrumental": FileResponse(instrumental_path, media_type="audio/wav", filename="instrumental.wav") if instrumental_path else None
    }
    