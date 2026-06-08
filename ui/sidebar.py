import logging
import streamlit as st
from qdrant_client import QdrantClient
from core.parser import parse_pdf
from core.session import clear_messages

logger = logging.getLogger(__name__)

def render_sidebar(client: QdrantClient):
    """Renders the sidebar for document upload and database maintenance."""
    with st.sidebar:
        # Use vh (viewport height) for responsive vertical centering without scrollbars
        st.markdown("<div style='height: 20vh;'></div>", unsafe_allow_html=True)
        
        st.markdown("### 📤 Upload Study Material")
        uploaded_files = st.file_uploader(
            "Upload PDF Lecture Notes, Textbooks, or Slides",
            type=["pdf"],
            accept_multiple_files=True
        )
        
        process_btn = st.button("Process Documents", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🧹 Database Maintenance")
        if st.button("Clear Vector Database", use_container_width=True, type="secondary"):
            _handle_clear_database(client)
            
        if process_btn:
            _handle_process_documents(client, uploaded_files)


def _handle_clear_database(client: QdrantClient):
    if client:
        try:
            logger.info("User requested to clear the vector database.")
            if client.collection_exists("academic_notes"):
                client.delete_collection("academic_notes")
                logger.info("Collection 'academic_notes' successfully deleted.")
            else:
                logger.info("Collection 'academic_notes' does not exist. No action needed.")
            
            st.success("Database successfully cleared!")
            clear_messages()
            st.rerun()
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            st.error(f"Error clearing database: {e}")
    else:
        st.warning("Database client not initialized.")


def _handle_process_documents(client: QdrantClient, uploaded_files):
    if not uploaded_files:
        st.sidebar.warning("Please upload at least one PDF file first.")
    elif not client:
        st.sidebar.error("Database client is not available.")
    else:
        with st.spinner("Parsing PDFs & Indexing with FastEmbed ONNX..."):
            documents = []
            metadatas = []
            
            for file in uploaded_files:
                try:
                    logger.info(f"Reading and parsing uploaded file: {file.name}")
                    file_bytes = file.read()
                    parsed_pages = parse_pdf(file_bytes, file.name)
                    
                    for page in parsed_pages:
                        documents.append(page["text"])
                        metadatas.append({
                            "filename": page["filename"],
                            "page_num": page["page_num"]
                        })
                    logger.info(f"Successfully extracted {len(parsed_pages)} pages from {file.name}")
                except Exception as parse_err:
                    logger.error(f"Error parsing {file.name}: {parse_err}")
                    st.sidebar.error(f"Error parsing {file.name}: {parse_err}")
            
            if documents:
                try:
                    logger.info(f"Adding {len(documents)} documents to Qdrant collection 'academic_notes'...")
                    # Implicitly compute embeddings using FastEmbed BGE Small and add to local database
                    client.add(
                        collection_name="academic_notes",
                        documents=documents,
                        metadata=metadatas
                    )
                    logger.info("Indexing completed successfully!")
                    st.sidebar.success(f"Successfully indexed {len(documents)} pages from {len(uploaded_files)} file(s)!")
                except Exception as upload_err:
                    logger.error(f"Failed indexing vectors: {upload_err}")
                    st.sidebar.error(f"Failed indexing vectors: {upload_err}")
            else:
                st.sidebar.warning("No readable text content extracted from the uploaded files.")
