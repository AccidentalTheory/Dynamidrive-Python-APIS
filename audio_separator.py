import os
import logging
from ultimatevocalremover import Separator as UVRSeparator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Separator:
    def __init__(self, model_name="BS-RoFormer"):
        """
        Initialize the UVR Separator with the specified model (default: BS-RoFormer).
        """
        try:
            # Initialize UVR Separator with the specified model
            # BS-RoFormer is a model name supported by UVR
            self.separator = UVRSeparator(model_name=model_name)
            logger.info(f"Initialized UVR Separator with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Separator: {str(e)}")
            raise

    def separate(self, input_path, output_dir, model_name=None):
        """
        Separate the audio file into multiple tracks.
        Returns a list of output filenames.
        """
        try:
            # Use the specified model if provided, otherwise use the initialized model
            if model_name:
                self.separator.model_name = model_name
                logger.info(f"Switching to model: {model_name}")

            # Perform separation
            # UVR typically outputs files like 'vocals.wav', 'drums.wav', etc.
            # Ensure output_dir exists
            os.makedirs(output_dir, exist_ok=True)
            output_files = self.separator.separate(
                audio_file=input_path,
                output_dir=output_dir,
                output_format="mp3"  # Match the expected format for download
            )

            # UVR returns a list of full paths; extract just the filenames
            output_filenames = [os.path.basename(path) for path in output_files]
            return output_filenames

        except Exception as e:
            logger.error(f"Separation failed: {str(e)}")
            raise