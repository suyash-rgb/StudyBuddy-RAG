import os
import logging
import streamlit as st
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

@st.cache_resource
def get_qdrant_client() -> QdrantClient:
    """
    Initializes and returns a cached QdrantClient pointing to the local storage path.
    Ensures that the 'academic_notes' collection is configured natively.
    """
    db_path = "./qdrant_db"
    os.makedirs(db_path, exist_ok=True)
    
    # Connect to Qdrant local storage
    logger.info(f"Connecting to Qdrant local storage at: {db_path}")
    client = QdrantClient(path=db_path)
    
    # Configure client to use the FastEmbed model natively
    logger.info("Configuring Qdrant client to use FastEmbed model natively: 'BAAI/bge-small-en-v1.5'")
    client.set_model("BAAI/bge-small-en-v1.5")
    
    return client

