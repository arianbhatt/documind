from typing import Any, List, Tuple, Optional, TypedDict
# import streamlit as st # <-- REMOVED
import io
import csv
import fitz  # PyMuPDF
import logging
# from langchain.text_splitters import RecursiveCharacterTextSplitter # <-- OLD IMPORT
from langchain_text_splitters import RecursiveCharacterTextSplitter # <-- CORRECTED IMPORT
from .config import Config
from werkzeug.datastructures import FileStorage # <-- ADDED for Flask file objects

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatMessage(TypedDict):
    role: str
    content: str
    timestamp: str

class PDFProcessor:
    def __init__(self, config: Optional[dict] = None):
        """Initialize the PDF processor with optional configuration settings."""
        self.config_settings = config or {}
    
    @staticmethod
    def extract_pdf_text(pdf_docs: List[FileStorage]) -> Tuple[str, List[dict]]:
        """
        Extract text from PDF documents with detailed error handling and metadata.
        
        Args:
            pdf_docs (List[FileStorage]): List of uploaded PDF files from Flask/Werkzeug.
        
        Returns:
            Tuple[str, List[dict]]: Extracted text and file processing metadata.
        """
        all_text = ""
        file_metadata = []
        
        for pdf in pdf_docs:
            filename = pdf.filename # <-- Get filename from FileStorage
            try:
                logger.info(f"Processing file: {filename}")
                # Use fitz (PyMuPDF) for robust PDF text extraction
                # Read from the file stream using .read()
                pdf_document = fitz.open(stream=pdf.read(), filetype="pdf")
                
                if pdf_document.is_encrypted:
                    logger.warning(f"⚠️ {filename} is encrypted. Skipping.")
                    file_metadata.append({
                        "filename": filename,
                        "status": "skipped",
                        "reason": "encrypted"
                    })
                    continue
                
                text_from_pdf = ""
                for page_num in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_num)
                    text_from_pdf += page.get_text()
                
                all_text += text_from_pdf + "\n\n" # Add separator
                
                file_metadata.append({
                    "filename": filename,
                    "status": "success",
                    "pages": pdf_document.page_count,
                    "extracted_chars": len(text_from_pdf)
                })
                logger.info(f"Successfully extracted text from {filename}.")

            except fitz.EmptyFileError:
                logger.warning(f"⚠️ {filename} is an empty PDF file. Skipping.")
                file_metadata.append({
                    "filename": filename,
                    "status": "skipped",
                    "reason": "empty file"
                })
            except Exception as e:
                logger.error(f"Failed to extract text from {filename}: {e}", exc_info=True)
                # st.error(f"Error processing {filename}: {e}.") # <-- REMOVED
                file_metadata.append({
                    "filename": filename,
                    "status": "failed",
                    "reason": str(e)
                })
                # We don't re-raise, to allow processing other files
        
        return all_text, file_metadata

    @staticmethod
    def get_text_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Splits a given text into smaller chunks for processing.
        """
        if not text:
            logger.warning("No text provided for chunking. Returning empty list.")
            return []
        
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len
            )
            chunks = text_splitter.split_text(text)
            logger.info(f"Text split into {len(chunks)} chunks with size {chunk_size} and overlap {chunk_overlap}.")
            return chunks
        except Exception as e:
            logger.error(f"Failed to split text into chunks: {e}")
            raise

    @staticmethod
    def save_chat_history(chat_history: List[ChatMessage], filename: str = "chat_summary.csv") -> Optional[str]:
        """
        Generates chat history as a CSV string.
        (Removed Streamlit download button)
        
        Args:
            chat_history (List[ChatMessage]): List of chat messages.
            filename (str): Name of the output CSV file (no longer used here).
            
        Returns:
            Optional[str]: The CSV data as a string, or None if no history.
        """
        try:
            if not chat_history:
                logger.info("No chat history to save.")
                return None

            with io.StringIO() as output:
                writer = csv.writer(output)
                writer.writerow(['Role', 'Message', 'Timestamp'])
                
                for message in chat_history:
                    role = message.get('role', 'N/A')
                    content = message.get('content', 'N/A')
                    timestamp = message.get('timestamp', 'N/A')
                    writer.writerow([role, content, timestamp])
                
                logger.info("Chat history CSV data generated.")
                return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to create chat history CSV: {e}")
            # st.error(f"Error saving chat history: {e}") # <-- REMOVED
            raise