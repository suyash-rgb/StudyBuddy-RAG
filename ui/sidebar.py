import logging
import os
import shutil
import streamlit as st
from qdrant_client import QdrantClient
from core.parser import parse_document
from core.session import clear_messages, add_indexed_file, clear_indexed_files
logger = logging.getLogger(__name__)

def render_sidebar(client: QdrantClient):
    """Renders the sidebar for document upload and database maintenance."""
    with st.sidebar:
        st.markdown("""
            <style>
            [data-testid="stSidebarUserContent"] {
                padding-top: 2rem !important;
            }
            [data-testid="stSidebarContent"] {
                overflow: hidden !important;
            }
            [data-testid="stSidebar"] ::-webkit-scrollbar {
                display: none !important;
                width: 0px !important;
                background: transparent !important;
            }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("### 📤 Upload Study Material")
        uploaded_files = st.file_uploader(
            "Upload Lecture Notes, Textbooks, Slides or Images",
            type=["pdf", "docx", "xlsx", "csv", "txt", "jsonl", "pptx", "png", "jpg", "jpeg"],
            accept_multiple_files=True
        )
        
        process_btn = st.button("Process Documents", width="stretch")
        
        st.markdown("---")
        st.markdown("### 🧹 Database Maintenance")
        if st.button("Clear Vector Database", width="stretch", type="secondary"):
            _handle_clear_database(client)
            
        if process_btn:
            _handle_process_documents(client, uploaded_files)


def _handle_clear_database(client: QdrantClient):
    try:
        logger.info("User requested to clear the vector database.")
        if client and client.collection_exists("academic_notes"):
            client.delete_collection("academic_notes")
        
        # Delete ephemeral extracted images
        if os.path.exists("extracted_images"):
            shutil.rmtree("extracted_images", ignore_errors=True)
            
        from core.llm_engine import clear_document_vocabulary
        clear_document_vocabulary()
            
        st.success("Database and ephemeral images successfully cleared!")
        clear_messages()
        clear_indexed_files()
        st.rerun()
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        st.error(f"Error clearing database: {e}")


def _handle_process_documents(client: QdrantClient, uploaded_files):
    if not uploaded_files:
        st.sidebar.warning("Please upload at least one document first.")
    elif not client:
        st.sidebar.error("Database client is not available.")
    else:
        with st.spinner("Parsing documents & Indexing with FastEmbed ONNX..."):
            documents = []
            metadatas = []
            
            for file in uploaded_files:
                try:
                    logger.info(f"Reading and parsing uploaded file: {file.name}")
                    file_bytes = file.read()
                    parsed_pages = parse_document(file_bytes, file.name)
                    
                    for page in parsed_pages:
                        # Prepend filename to the indexed text to significantly improve semantic matching for file-specific queries
                        enhanced_text = f"Document Name: {file.name}\n\n{page['text']}"
                        documents.append(enhanced_text)
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
                    
                    for file in uploaded_files:
                        add_indexed_file(file.name)
                        
                    from core.llm_engine import update_document_vocabulary
                    update_document_vocabulary(documents)
                        
                    logger.info("Indexing completed successfully!")
                    st.sidebar.success(f"Successfully indexed {len(documents)} pages from {len(uploaded_files)} file(s)!")
                except Exception as upload_err:
                    logger.error(f"Failed indexing vectors: {upload_err}")
                    st.sidebar.error(f"Failed indexing vectors: {upload_err}")
            else:
                st.sidebar.warning("No readable text content extracted from the uploaded files.")
