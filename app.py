import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file at application startup
load_dotenv()

# Configure page layout and style
st.set_page_config(
    page_title="PdfInsight - Academic Study Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling relying on native Light/Dark themes
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');
    
    /* Use a serif font for headings (academic) and Inter for body text */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Lora', serif !important;
    }
    
    /* Academic subtle styling */
    .stButton>button {
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease-in-out !important;
        width: 100%;
        margin-top: 10px;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Chat message separation */
    .stChatMessage {
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid var(--secondary-background-color);
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Postponed imports to allow loading variables first
from core.database import get_qdrant_client
from core.parser import parse_pdf
from core.llm_engine import generate_study_response

# Main application header
st.title("📚 PdfInsight")
st.subheader("Lightweight Local-First Academic Study Assistant")

# Initialize database client
client = None
try:
    client = get_qdrant_client()
except Exception as e:
    st.error(f"Failed to initialize local Qdrant client: {e}")

# Sidebar dashboard
with st.sidebar:
    st.markdown("### 📤 Upload Study Material")
    uploaded_files = st.file_uploader(
        "Upload PDF Lecture Notes, Textbooks, or Slides",
        type=["pdf"],
        accept_multiple_files=True
    )
    
    process_btn = st.button("Process & Index Documents", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🧹 Database Maintenance")
    if st.button("Clear Vector Database", use_container_width=True, type="secondary"):
        if client:
            try:
                client.delete_collection("academic_notes")
                # Re-create database configuration
                from qdrant_client.models import Distance, VectorParams
                client.create_collection(
                    collection_name="academic_notes",
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                st.success("Database successfully cleared!")
                st.session_state.messages = []
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing database: {e}")
        else:
            st.warning("Database client not initialized.")

# Handling PDF processing
if process_btn:
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
                    file_bytes = file.read()
                    parsed_pages = parse_pdf(file_bytes, file.name)
                    
                    for page in parsed_pages:
                        documents.append(page["text"])
                        metadatas.append({
                            "filename": page["filename"],
                            "page_num": page["page_num"]
                        })
                except Exception as parse_err:
                    st.sidebar.error(f"Error parsing {file.name}: {parse_err}")
            
            if documents:
                try:
                    # Implicitly compute embeddings using FastEmbed BGE Small and add to local database
                    client.add(
                        collection_name="academic_notes",
                        documents=documents,
                        metadata=metadatas
                    )
                    st.sidebar.success(f"Successfully indexed {len(documents)} pages from {len(uploaded_files)} file(s)!")
                except Exception as upload_err:
                    st.sidebar.error(f"Failed indexing vectors: {upload_err}")
            else:
                st.sidebar.warning("No readable text content extracted from the uploaded files.")

# Session State for Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("references"):
            with st.expander("🔍 Verified Context References"):
                for idx, ref in enumerate(msg["references"]):
                    st.markdown(f"**Reference {idx+1}:** {ref['filename']} (Page {ref['page_num']}) - *Similarity: {ref['score']:.2f}*")
                    st.code(ref["text"], language="text")

# Chat Input & RAG Execution
if query := st.chat_input("Ask a question about your study documents..."):
    # Render user query
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})
    
    # RAG Logic
    if not client:
        with st.chat_message("assistant"):
            st.error("Database client is not available. Check configuration details.")
    else:
        with st.spinner("Querying local vector database & invoking Groq LLM..."):
            try:
                # Check point count to determine if DB is empty
                collection_info = client.get_collection("academic_notes")
                points_count = collection_info.points_count
            except Exception:
                points_count = 0
                
            if points_count == 0:
                with st.chat_message("assistant"):
                    st.warning("⚠️ No documents indexed yet. Please upload study materials in the sidebar and click 'Process & Index Documents' first.")
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "⚠️ No documents indexed yet. Please upload study materials in the sidebar and click 'Process & Index Documents' first."
                })
            else:
                try:
                    # Semantic search via FastEmbed (implicitly calls BAAI/bge-small-en-v1.5 to embed query)
                    results = client.query(
                        collection_name="academic_notes",
                        query_text=query,
                        limit=3
                    )
                    
                    context_blocks = []
                    references = []
                    
                    for r in results:
                        doc_text = r.document
                        meta = r.metadata
                        fname = meta.get("filename", "Unknown Document")
                        pnum = meta.get("page_num", "?")
                        
                        context_blocks.append(f"Source: {fname} (Page {pnum})\nContent: {doc_text}")
                        references.append({
                            "filename": fname,
                            "page_num": pnum,
                            "text": doc_text,
                            "score": r.score
                        })
                        
                    context_str = "\n\n---\n\n".join(context_blocks)
                    
                    # Generate response via Groq
                    answer = generate_study_response(query, context_str)
                    
                    # Render assistant response
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        with st.expander("🔍 Verified Context References"):
                            for idx, ref in enumerate(references):
                                st.markdown(f"**Reference {idx+1}:** {ref['filename']} (Page {ref['page_num']}) - *Similarity: {ref['score']:.2f}*")
                                st.code(ref["text"], language="text")
                                
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "references": references
                    })
                except Exception as rag_err:
                    with st.chat_message("assistant"):
                        st.error(f"RAG Pipeline Error: {rag_err}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"⚠️ RAG Pipeline Error: {rag_err}"
                    })
