import logging
import re
import os
import glob
import html
import zlib
import base64
import string
import streamlit as st
import streamlit.components.v1 as components
from qdrant_client import QdrantClient
from qdrant_client import models
from core.llm_engine import generate_study_response
from core.session import get_messages, add_message, get_indexed_files

logger = logging.getLogger(__name__)

def plantuml_encode(plantuml_text: str) -> str:
    """Compress and encode PlantUML text for a PlantUML server."""
    plantuml_alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase + '-_'
    base64_alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
    
    trans_table = bytes.maketrans(base64_alphabet.encode('utf-8'), plantuml_alphabet.encode('utf-8'))
    
    # 1. Deflate compression
    zlibbed_str = zlib.compress(plantuml_text.encode('utf-8'))
    
    # 2. Remove zlib header/footer
    compressed_string = zlibbed_str[2:-4]
    
    # 3. Base64 encode and translate to PlantUML alphabet
    return base64.b64encode(compressed_string).translate(trans_table).decode('utf-8')

def render_mermaid(code: str):
    """Renders Mermaid diagram using the remote Mermaid Ink API."""
    import json
    import urllib.request
    from core.export import sanitize_mermaid_code
    try:
        code = sanitize_mermaid_code(code)
        payload = json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").replace("=", "")
        url = f"https://mermaid.ink/img/{encoded}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            img_data = response.read()
            
        b64 = base64.b64encode(img_data).decode('utf-8')
        st.markdown(f'<div style="text-align: center; margin: 15px 0;"><img src="data:image/jpeg;base64,{b64}" style="max-width: 100%; height: auto; max-height: 500px; display: block; margin: 0 auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning("Diagram could not be rendered (syntax error). Falling back to code:")
        st.code(code, language="mermaid")

def render_graphviz(code: str):
    """Renders DOT Graphviz diagram using Streamlit native widget."""
    try:
        st.graphviz_chart(code, use_container_width=False)
    except Exception as e:
        st.error(f"Error rendering Graphviz diagram: {e}")
        st.code(code, language="dot")

def render_plantuml(code: str):
    """Renders PlantUML diagram using the remote PlantUML image API."""
    import urllib.request
    try:
        encoded = plantuml_encode(code)
        url = f"https://www.plantuml.com/plantuml/png/{encoded}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            img_data = response.read()
            
        b64 = base64.b64encode(img_data).decode('utf-8')
        st.markdown(f'<div style="text-align: center; margin: 15px 0;"><img src="data:image/png;base64,{b64}" style="max-width: 100%; height: auto; max-height: 500px; display: block; margin: 0 auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"/></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning("Diagram could not be rendered (syntax error). Falling back to code:")
        st.code(code, language="plantuml")

def render_d2(code: str):
    """Renders D2 diagram in a Streamlit HTML component using WASM via CDN."""
    js_safe_code = code.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    html_content = f"""
    <div id="d2-container" style="width: 100%; height: 100%;">Rendering D2 Diagram...</div>
    <script type="module">
        import {{ D2 }} from 'https://esm.sh/@terrastruct/d2';
        
        async function init() {{
            try {{
                const d2 = new D2();
                const code = `{js_safe_code}`;
                const result = await d2.compile(code);
                const svg = await d2.render(result.diagram, result.renderOptions);
                const container = document.getElementById('d2-container');
                container.innerHTML = svg;
            }} catch (err) {{
                document.getElementById('d2-container').innerHTML = '<pre style="color:red;">Error: ' + err.message + '</pre>';
            }}
        }}
        init();
    </script>
    """
    components.html(html_content, height=450, scrolling=True)

def render_inline_diagram(lang: str, code: str):
    """Routes the diagram rendering to the appropriate tool renderer."""
    lang = lang.lower().strip()
    if lang == "mermaid":
        render_mermaid(code)
    elif lang in ("graphviz", "dot"):
        render_graphviz(code)
    elif lang == "plantuml":
        render_plantuml(code)
    elif lang == "d2":
        render_d2(code)

def display_response_with_diagrams(text: str):
    """
     Splits the Markdown response and renders sections sequentially,
     replacing diagram fenced blocks with their actual rendered component widgets.
     """
    pattern = r"```(mermaid|graphviz|dot|plantuml|d2)\b[^\n]*\r?\n(.*?)\r?\n\s*```"
    parts = re.split(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    
    i = 0
    while i < len(parts):
        normal_text = parts[i]
        if normal_text.strip():
            st.markdown(normal_text, unsafe_allow_html=True)
            
        if i + 2 < len(parts):
            lang = parts[i+1]
            code = parts[i+2]
            render_inline_diagram(lang, code)
            i += 3
        else:
            i += 1

def render_chat_interface(client: QdrantClient):
    """Renders the chat history and input, handling RAG execution."""
    
    # Display Chat History
    messages = get_messages()
    
    indexed_files = get_indexed_files()
    selected_file = "All Documents"
    if indexed_files:
        selected_file = st.selectbox("Search Context (Filter by File)", ["All Documents"] + indexed_files)
        st.markdown("<br>", unsafe_allow_html=True)

    # Place settings at the stable top of the chat area to avoid layout shifts
    st.markdown("**⚙️ Query Options & Tools**")
    col1, col2 = st.columns([1, 1])
    with col1:
        add_diagram = st.toggle("Enable Diagram Generation", value=st.session_state.get("add_diagram", False), key="add_diagram")
    with col2:
        messages = get_messages()
        if messages:
            if st.button("📥 Prepare PDF Export", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    from core.export import export_conversation_to_pdf
                    st.session_state.pdf_bytes = export_conversation_to_pdf()
            if "pdf_bytes" in st.session_state:
                st.download_button(
                    label="Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name="conversation_export.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
    st.markdown("---")

    for idx, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                display_response_with_diagrams(msg["content"])
            else:
                st.markdown(msg["content"], unsafe_allow_html=True)
            
            if msg.get("images"):
                cols = st.columns(min(len(msg["images"]), 3))
                for i, img_path in enumerate(msg["images"]):
                    with cols[i % 3]:
                        st.image(img_path, use_container_width=True)
                        
            if msg.get("references"):
                with st.expander("🔍 Verified Context References"):
                    for idx_ref, ref in enumerate(msg["references"]):
                        st.markdown(f"**Reference {idx_ref+1}:** {ref['filename']} (Page {ref['page_num']}) - *Similarity: {ref['score']:.2f}*")
                        st.code(ref["text"], language="text")

            # Inline Edit Response & Add Notes (only for assistant messages)
            if msg["role"] == "assistant":
                with st.expander("📝 Edit Response & Add Notes"):
                    edited_content = st.text_area(
                        "Edit Response Markdown",
                        value=msg["content"],
                        key=f"edit_text_{idx}",
                        height=150
                    )
                    
                    uploaded_image = st.file_uploader(
                        "Upload and embed custom image",
                        type=["png", "jpg", "jpeg"],
                        key=f"upload_image_{idx}"
                    )
                    
                    if uploaded_image:
                        os.makedirs("uploaded_images", exist_ok=True)
                        img_path = os.path.join("uploaded_images", uploaded_image.name)
                        with open(img_path, "wb") as f:
                            f.write(uploaded_image.read())
                        
                        if "images" not in msg:
                            msg["images"] = []
                        if img_path not in msg["images"]:
                            msg["images"].append(img_path)
                            st.success(f"Uploaded {uploaded_image.name}!")
                            st.rerun()
                            
                    if edited_content != msg["content"]:
                        if st.button("Save Changes", key=f"save_edit_{idx}"):
                            msg["content"] = edited_content
                            st.success("Response updated!")
                            st.rerun()

    # Render confirmation message & buttons if awaiting diagram confirmation
    if st.session_state.get("awaiting_diagram_confirmation", False):
        with st.chat_message("assistant"):
            st.markdown("Would you like a diagram included in the answer?")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("Yes, include a diagram", key="confirm_diagram_yes"):
                    st.session_state.awaiting_diagram_confirmation = False
                    st.session_state.diagram_confirmation_choice = "Yes"
                    st.rerun()
            with confirm_col2:
                if st.button("No, text only", key="confirm_diagram_no"):
                    st.session_state.awaiting_diagram_confirmation = False
                    st.session_state.diagram_confirmation_choice = "No"
                    st.rerun()

    # 1. Check if we have a confirmation choice from a previous interaction
    confirm_choice = st.session_state.get("diagram_confirmation_choice")
    if confirm_choice is not None:
        query = st.session_state.get("pending_query")
        selected_file = st.session_state.get("pending_selected_file")
        
        # Clear state variables first
        st.session_state.diagram_confirmation_choice = None
        st.session_state.pending_query = None
        st.session_state.pending_selected_file = None
        
        if confirm_choice == "Yes":
            from core.llm_engine import select_diagram_tool
            with st.spinner("Selecting diagram tool..."):
                tool = select_diagram_tool(query)
            _handle_rag_query(client, query, selected_file, diagram_tool=tool)
        else:
            _handle_rag_query(client, query, selected_file, diagram_tool=None)

    # 2. Otherwise handle new input
    query = st.chat_input("Ask a question about your study documents...")
    if query:
        # Store and display user query
        add_message("user", query)
        with st.chat_message("user"):
            st.markdown(query)
            
        # Check for Intent (Spam Check + Image Interception)
        from core.llm_engine import analyze_query_intent
        
        with st.spinner("Analyzing intent..."):
            intent = analyze_query_intent(query)
            
        if intent.get("is_bogus"):
            msg = "⚠️ Please try paraphrasing and ask again."
            add_message("assistant", msg)
            with st.chat_message("assistant"):
                st.markdown(msg)
        elif intent.get("is_image_query"):
            page_num = intent.get("page_num")
            _handle_image_query(query, page_num, selected_file, client)
        else:
            # Execute RAG
            if not client:
                with st.chat_message("assistant"):
                    logger.warning("Query rejected because Qdrant client is not available.")
                    st.error("Database client is not available. Check configuration details.")
            else:
                if add_diagram:
                    from core.llm_engine import detect_diagram_scope
                    with st.spinner("Detecting diagram scope..."):
                        scope = detect_diagram_scope(query)
                        
                    if scope == "Yes":
                        from core.llm_engine import select_diagram_tool
                        with st.spinner("Selecting diagram tool..."):
                            tool = select_diagram_tool(query)
                        _handle_rag_query(client, query, selected_file, diagram_tool=tool)
                    elif scope == "Ambiguous":
                        st.session_state.awaiting_diagram_confirmation = True
                        st.session_state.pending_query = query
                        st.session_state.pending_selected_file = selected_file
                        st.rerun()
                    else:  # No
                        _handle_rag_query(client, query, selected_file, diagram_tool=None)
                else:
                    _handle_rag_query(client, query, selected_file, diagram_tool=None)

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

def _handle_rag_query(client: QdrantClient, query: str, selected_file: str, diagram_tool: str | None = None):
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
                answer = generate_study_response(query, context_str, diagram_tool=diagram_tool)
                
                # Render assistant response with diagrams
                with st.chat_message("assistant"):
                    display_response_with_diagrams(answer)
                    with st.expander("🔍 Verified Context References"):
                        for idx, ref in enumerate(references):
                            st.markdown(f"**Reference {idx+1}:** {ref['filename']} (Page {ref['page_num']}) - *Similarity: {ref['score']:.2f}*")
                            st.code(ref["text"], language="text")
                            
                add_message("assistant", answer, references=references)
            except Exception as rag_err:
                with st.chat_message("assistant"):
                    st.error(f"RAG Pipeline Error: {rag_err}")
                add_message("assistant", f"⚠️ RAG Pipeline Error: {rag_err}")
