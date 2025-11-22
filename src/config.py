import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    def __init__(self, load_env=True):
        """Initialize configuration and load environment variables."""
        if load_env:
            load_dotenv()
        logger.info("Environment variables loaded.")

    def get_app_settings(self) -> Dict[str, Any]:
        """
        Retrieve application-wide settings.
        """
        settings = {
            'embedding_type': os.getenv('EMBEDDING_TYPE', 'huggingface').lower(),
            'model_type': os.getenv('MODEL_TYPE', 'google').lower(),
            'model_path': os.getenv('MODEL_PATH', 'models/gemma-2-2b-it.q4_k_m.gguf'), # Path for local model
            'chunk_size': int(os.getenv('CHUNK_SIZE', 1000)),
            'chunk_overlap': int(os.getenv('CHUNK_OVERLAP', 200))
        }
        logger.info(f"Application settings retrieved: {settings}")
        return settings

    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Validate application settings for either Google or Local models.
        """
        required_keys = ['embedding_type', 'model_type', 'chunk_size', 'chunk_overlap']
        if not all(key in settings for key in required_keys):
            logger.error(f"Missing required settings keys: {required_keys}")
            return False
        
        # Validate embedding type (still local-only)
        if settings['embedding_type'] not in ["huggingface"]:
            logger.error(f"Invalid embedding type: {settings['embedding_type']}. Only 'huggingface' (local) is supported.")
            return False
        
        # Validate model type
        if settings['model_type'] not in ["local", "google"]:
             logger.warning(f"Initial model type '{settings['model_type']}' is set, but user can select in UI.")

        # Validate conditional requirements
        # We check this at runtime in the Flask app now, but good to log a warning
        if not os.getenv("GOOGLE_API_KEY") and not settings['model_path']:
             logger.warning("Missing credentials. Please set GOOGLE_API_KEY or a valid MODEL_PATH in your .env file.")
             # We return True here, as the app might be used in a way that doesn't need both
             # The Flask get_llm_instance will handle the hard failure.

        if not isinstance(settings['chunk_size'], int) or settings['chunk_size'] <= 0:
            logger.error(f"Invalid chunk size: {settings['chunk_size']}")
            return False
        
        if not isinstance(settings['chunk_overlap'], int) or settings['chunk_overlap'] < 0:
            logger.error(f"Invalid chunk overlap: {settings['chunk_overlap']}")
            return False
        
        logger.info("Settings validated successfully.")
        return True