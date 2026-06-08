import os
import logging
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger(__name__)

@st.cache_resource
def get_qdrant_client() -> QdrantClient:
    """
    Initializes and returns a cached QdrantClient pointing to the local storage path.
    Ensures that the 'academic_notes' collection is created with proper vector configurations
    matching the 'BAAI/bge-small-en-v1.5' FastEmbed model (384 dimensions).
    """
    db_path = "./qdrant_db"
    os.makedirs(db_path, exist_ok=True)
    
    # Connect to Qdrant local storage
    logger.info(f"Connecting to Qdrant local storage at: {db_path}")
    client = QdrantClient(path=db_path)
    
    # Configure client to use the FastEmbed model natively
    logger.info("Configuring Qdrant client to use FastEmbed model natively: 'BAAI/bge-small-en-v1.5'")
    client.set_model("BAAI/bge-small-en-v1.5")
    
    collection_name = "academic_notes"
    
    # Ensure collection exists. If not, create it with 384 dimensions for BGE Small.
    try:
        if not client.collection_exists(collection_name=collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=384, 
                    distance=Distance.COSINE
                )
            )
    except Exception as e:
        st.error(f"Failed to check or create Qdrant collection: {str(e)}")
        
    return client
