import logging
import re
import os
import glob
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client import models
from core.llm_engine import generate_study_response
from core.session import get_messages, add_message, get_indexed_files

logger = logging.getLogger(__name__)

def render_chat_interface(client: QdrantClient):
    """Renders the chat history and input, handling RAG execution."""
    
    # Display Chat History
    messages = get_messages()
    
    indexed_files = get_indexed_files()
    selected_file = "All Documents"
    if indexed_files:
        selected_file = st.selectbox("Search Context (Filter by File)", ["All Documents"] + indexed_files)
        st.markdown("<br>", unsafe_allow_html=True)

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)
            
            if msg.get("images"):
                cols = st.columns(min(len(msg["images"]), 3))
                for i, img_path in enumerate(msg["images"]):
                    with cols[i % 3]:
                        st.image(img_path, use_container_width=True)
                        
            if msg.get("references"):
                with st.expander("🔍 Verified Context References"):
                    for idx, ref in enumerate(msg["references"]):
                        st.markdown(f"**Reference {idx+1}:** {ref['filename']} (Page {ref['page_num']}) - *Similarity: {ref['score']:.2f}*")
                        st.code(ref["text"], language="text")

    # Export Conversation Button (Bottom Right)
    if messages:
        col1, col2, col3 = st.columns([6, 2, 2])
        with col3:
            from core.export import export_conversation_to_pdf
            st.download_button(
                label="📥 Export PDF",
                data=export_conversation_to_pdf(),
                file_name="conversation_export.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    # Chat Input & RAG Execution
    if query := st.chat_input("Ask a question about your study documents..."):
        # Store and display user query
        add_message("user", query)
        with st.chat_message("user"):
            st.markdown(query)
            
        # Check for Image Interception via LLM Intent (Bypass RAG)
        from core.llm_engine import classify_image_intent
        
        with st.spinner("Analyzing intent..."):
            intent = classify_image_intent(query)
            
        if intent.get("is_image_query"):
            page_num = intent.get("page_num")
            _handle_image_query(query, page_num, selected_file, client)
        else:
            # Execute RAG
            if not client:
                with st.chat_message("assistant"):
                    logger.warning("Query rejected because Qdrant client is not available.")
                    st.error("Database client is not available. Check configuration details.")
            else:
                _handle_rag_query(client, query, selected_file)

def _handle_image_query(query: str, page_num: int | str | None, selected_file: str, client: QdrantClient):
    if not selected_file or selected_file == "All Documents":
        msg = "⚠️ Please select a specific PDF file from the **Search Context** dropdown to view its images."
        add_message("assistant", msg)
        with st.chat_message("assistant"):
            st.markdown(msg)
        return
        
    img_dir = os.path.join("extracted_images", selected_file)
    if not os.path.exists(img_dir):
        msg = f"No images found for `{selected_file}`. Are you sure it's a PDF that contains images?"
        add_message("assistant", msg)
        with st.chat_message("assistant"):
            st.markdown(msg)
        return
        
    # Tier 2: Computed Routing ("last" page)
    if page_num == "last":
        all_images = glob.glob(os.path.join(img_dir, "page_*_img_*.*"))
        if all_images:
            max_page = -1
            for img in all_images:
                try:
                    max_page = max(max_page, int(os.path.basename(img).split("_")[1]))
                except Exception:
                    pass
            page_num = max_page if max_page != -1 else None

    # Tier 3: Semantic Hybrid Search
    if page_num is None:
        if client:
            with st.spinner("Semantically routing to the best image..."):
                query_filter = models.Filter(
                    must=[models.FieldCondition(key="filename", match=models.MatchValue(value=selected_file))]
                )
                try:
                    results = client.query(
                        collection_name="academic_notes",
                        query_text=query,
                        query_filter=query_filter,
                        limit=1
                    )
                    if results and results[0].metadata.get("page_num"):
                        page_num = results[0].metadata["page_num"]
                except Exception as e:
                    logger.error(f"Hybrid search failed: {e}")

    if page_num is None:
        msg = f"No relevant embedded images were found in `{selected_file}` matching your query."
        add_message("assistant", msg)
        with st.chat_message("assistant"):
            st.markdown(msg)
        return
        
    pattern = os.path.join(img_dir, f"page_{page_num}_img_*.*")
    image_files = glob.glob(pattern)
    
    if not image_files:
        msg = f"No embedded images were found on **page {page_num}** of `{selected_file}`."
        add_message("assistant", msg)
        with st.chat_message("assistant"):
            st.markdown(msg)
        return
        
    msg = f"Here are the images extracted from **page {page_num}** of `{selected_file}`:"
        
    add_message("assistant", msg, images=image_files)
    
    with st.chat_message("assistant"):
        st.markdown(msg)
        cols = st.columns(min(len(image_files), 3))
        for i, img_path in enumerate(image_files):
            with cols[i % 3]:
                st.image(img_path, caption=f"Image {i+1}", use_container_width=True)

def _handle_rag_query(client: QdrantClient, query: str, selected_file: str):
    with st.spinner("Querying local vector database & invoking Groq LLM..."):
        try:
            # Check point count to determine if DB is empty
            collection_info = client.get_collection("academic_notes")
            points_count = collection_info.points_count
        except Exception:
            points_count = 0
            
        if points_count == 0:
            with st.chat_message("assistant"):
                logger.info("Query rejected because database is empty.")
                st.warning("⚠️ No documents indexed yet. Please upload study materials in the sidebar and click 'Process Documents' first.")
            add_message("assistant", "⚠️ No documents indexed yet. Please upload study materials in the sidebar and click 'Process Documents' first.")
        else:
            try:
                # Build metadata filter if a specific file is selected
                query_filter = None
                if selected_file and selected_file != "All Documents":
                    query_filter = models.Filter(
                        must=[
                            models.FieldCondition(
                                key="filename",
                                match=models.MatchValue(value=selected_file)
                            )
                        ]
                    )

                logger.info(f"Querying Qdrant for similar context to: '{query}' with filter: {selected_file}")
                # Semantic search via FastEmbed
                results = client.query(
                    collection_name="academic_notes",
                    query_text=query,
                    query_filter=query_filter,
                    limit=3
                )
                logger.info(f"Retrieved {len(results)} context blocks from database.")
                
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
                
                # Render assistant response with unsafe_allow_html=True for tables and <br>
                with st.chat_message("assistant"):
                    st.markdown(answer, unsafe_allow_html=True)
                    with st.expander("🔍 Verified Context References"):
                        for idx, ref in enumerate(references):
                            st.markdown(f"**Reference {idx+1}:** {ref['filename']} (Page {ref['page_num']}) - *Similarity: {ref['score']:.2f}*")
                            st.code(ref["text"], language="text")
                            
                add_message("assistant", answer, references=references)
            except Exception as rag_err:
                with st.chat_message("assistant"):
                    st.error(f"RAG Pipeline Error: {rag_err}")
                add_message("assistant", f"⚠️ RAG Pipeline Error: {rag_err}")
