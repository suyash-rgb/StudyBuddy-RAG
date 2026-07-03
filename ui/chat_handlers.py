import os
import glob
import logging
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client import models
from core.llm_engine import generate_study_response
from core.session import add_message

logger = logging.getLogger(__name__)

def _handle_image_query(query: str, page_num: int | str | None, selected_file: str, client: QdrantClient):
    if not selected_file or selected_file == "All Documents":
        msg = "⚠️ Please select a specific PDF file from the **Search Context** dropdown to view its images."
        add_message("assistant", msg)
        st.rerun()
        
    img_dir = os.path.join("extracted_images", selected_file)
    if not os.path.exists(img_dir):
        msg = f"No images found for `{selected_file}`. Are you sure it's a PDF that contains images?"
        add_message("assistant", msg)
        st.rerun()
        
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
        st.rerun()
        
    pattern = os.path.join(img_dir, f"page_{page_num}_img_*.*")
    image_files = glob.glob(pattern)
    
    if not image_files:
        msg = f"No embedded images were found on **page {page_num}** of `{selected_file}`."
        add_message("assistant", msg)
        st.rerun()
        
    msg = f"Here are the images extracted from **page {page_num}** of `{selected_file}`:"
        
    add_message("assistant", msg, images=image_files)
    st.rerun()

def _handle_rag_query(client: QdrantClient, query: str, selected_file: str, diagram_tool: str | None = None):
    with st.spinner("Querying local vector database & invoking Groq LLM..."):
        try:
            # Check point count to determine if DB is empty
            collection_info = client.get_collection("academic_notes")
            points_count = collection_info.points_count
        except Exception:
            points_count = 0
            
        if points_count == 0:
            logger.info("Query rejected because database is empty.")
            add_message("assistant", "⚠️ No documents indexed yet. Please upload study materials in the sidebar and click 'Process Documents' first.")
            st.rerun()
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
                answer = generate_study_response(query, context_str, diagram_tool=diagram_tool)
                
                add_message("assistant", answer, references=references)
                st.rerun()
            except Exception as rag_err:
                add_message("assistant", f"⚠️ RAG Pipeline Error: {rag_err}")
                st.rerun()
