# This file had no Streamlit dependencies and remains unchanged.
import logging
from typing import Any, Dict, List, Optional
from .config import Config # Ensure Config is imported if needed
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logging(level: str = 'INFO') -> None:
    """
    Configure logging for the application.
    
    Args:
        level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    root_logger.setLevel(logging_levels.get(level.upper(), logging.INFO))
    logger.info(f"Logging configured with level: {level.upper()}")


def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely retrieve a value from a dictionary.
    """
    return dictionary.get(key, default)

def validate_file_type(
    filename: str, 
    allowed_extensions: Optional[List[str]] = None
) -> bool:
    """
    Validate file type based on its extension.
    """
    if allowed_extensions is None:
        return True 

    if not isinstance(filename, str):
        logger.warning(f"Invalid filename type: {type(filename)}. Expected string.")
        return False

    file_extension = filename.split('.')[-1].lower()
    if file_extension in [ext.lower() for ext in allowed_extensions]:
        logger.info(f"File '{filename}' has a valid extension: .{file_extension}")
        return True
    else:
        logger.warning(f"File '{filename}' has an invalid extension: .{file_extension}. Allowed: {allowed_extensions}")
        return False

def generate_conversation_suggestions(vectorstore: Optional[Any], num_suggestions: int = 4) -> List[str]:
    """
    Generate context-aware conversation suggestions.
    """
    if vectorstore:
        try:
            sample_texts = vectorstore.similarity_search("document", k=num_suggestions * 2)
            
            common_topics = set()
            for text_doc in sample_texts:
                words = [word.lower() for word in text_doc.page_content.split() if len(word) > 3 and word.isalpha()]
                common_topics.update(words[:5])

            suggestions = list(common_topics)[:num_suggestions]
            
            formatted_suggestions = []
            for topic in suggestions:
                if topic not in ["the", "and", "for", "with", "from", "what", "how", "why"]:
                    formatted_suggestions.append(f"What is {topic}?")
            
            if len(formatted_suggestions) < num_suggestions:
                fallback_count = num_suggestions - len(formatted_suggestions)
                formatted_suggestions.extend(_get_fallback_suggestions()[:fallback_count])

            logger.info(f"Generated {len(formatted_suggestions)} context-based suggestions.")
            return formatted_suggestions
        except Exception as e:
            logger.error(f"Failed to generate context-aware suggestions: {e}")
    
    return _get_fallback_suggestions()

def _get_fallback_suggestions() -> List[str]:
    """Provides a list of fallback suggestions."""
    return [
        "Summarize key document points",
        "Extract main ideas",
        "Find key statistics",
        "List most frequent topics",
        "What is the main purpose of the document?"
    ]