from typing import List, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import logging
import os
# import streamlit as st # <-- REMOVED

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingSelector:
    @staticmethod
    def get_embedding_model(embedding_type: str = 'huggingface') -> Any:
        """
        Get the embedding model. Now defaults to and only supports HuggingFace local embeddings.
        """
        try:
            model_name = "BAAI/bge-base-en-v1.5"
            logger.info(f"Loading Hugging Face embedding model: {model_name}")
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'}, # Use 'cuda' if GPU is available
                encode_kwargs={'normalize_embeddings': True},
            )
        except Exception as e:
            logger.error(f"Failed to load Hugging Face embedding model: {e}")
            raise ValueError(f"Failed to load Hugging Face embedding model: {e}")

    @staticmethod
    def create_vectorstore(
        text_chunks: List[str],
        embedding_model: Any
    ) -> FAISS:
        """
        Create a FAISS vector store.
        """
        logger.info("Processing all documents locally to create vector store...")
        try:
            vectors = FAISS.from_texts(texts=text_chunks, embedding=embedding_model)
            logger.info("Vector store created successfully (local).")
            return vectors
        except Exception as e:
            logger.error(f"Failed to create vector store: {e}")
            # st.error(f"Failed to create vector store: {e}") # <-- REMOVED
            raise # Re-raise the exception for the Flask route