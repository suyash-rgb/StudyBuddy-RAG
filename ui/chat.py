import logging
import os
import streamlit as st
from qdrant_client import QdrantClient
from core.session import get_messages, add_message, get_indexed_files
from ui.diagrams import display_response_with_diagrams
from ui.chat_handlers import _handle_rag_query, _handle_image_query

logger = logging.getLogger(__name__)

@st.fragment
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
    
    # If there are no messages, add a spacer to push the input box to the bottom
    if not messages:
        st.markdown("<br>" * 15, unsafe_allow_html=True)
    
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
                if st.button("➕ Append to Notes", key=f"append_to_notes_{idx}", help="Send this response to your Master Notes"):
                    st.session_state.master_notes += f"\n\n{msg['content']}"
                    st.toast("Appended to Master Notes!")
                    
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
