# src/__init__.py
"""
Documind is a PDF Chat Application
A Flask application for interactive PDF document analysis.
"""

__version__ = "0.1.0"
__author__ = "Aryan Bhatt"
__email__ = "bhatt.aryan.2003@gmail.com"

# Import necessary modules and functions
from .pdf_processing import PDFProcessor
from .embeddings import EmbeddingSelector
from .conversation import ConversationEnhancer
from .config import Config
from .notes_manager import PersistentStorageManager
# from .notes_manager import PersistentStorageManager, setup_persistent_storage # <-- MODIFIED
from .utils import setup_logging, safe_get, validate_file_type, generate_conversation_suggestions

# Initialize logging
setup_logging()         
