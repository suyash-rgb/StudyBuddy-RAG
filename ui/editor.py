import streamlit as st
from ui.chat import display_response_with_diagrams
from core.export import export_notes_to_pdf

def render_notes_editor():
    """Renders the centralized Google Docs-like Markdown editor."""
    st.markdown("### 📝 My Notes")
    
    # Action Toolbar
    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            label="⬇️ Download Markdown",
            data=st.session_state.master_notes,
            file_name="StudyBuddy_Notes.md",
            mime="text/markdown",
            use_container_width=True
        )
    with col2:
        if st.button("📥 Prepare PDF", use_container_width=True, key="export_notes_pdf_btn"):
            with st.spinner("Generating PDF..."):
                pdf_bytes = export_notes_to_pdf(st.session_state.master_notes)
                if pdf_bytes:
                    st.session_state.notes_pdf_bytes = pdf_bytes
                    
        if "notes_pdf_bytes" in st.session_state:
            st.download_button(
                label="Click to Download PDF",
                data=st.session_state.notes_pdf_bytes,
                file_name="StudyBuddy_Notes.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_notes_pdf_action"
            )

    # Edit & Preview Tabs
    tab_edit, tab_preview = st.tabs(["✏️ Edit Mode", "👁️ Preview Mode"])
    
    with tab_edit:
        # Use a large text area for editing markdown
        updated_notes = st.text_area(
            "Editor",
            value=st.session_state.master_notes,
            height=650,
            key="master_notes_editor",
            label_visibility="collapsed"
        )
        
        # Update session state if the content changes
        if updated_notes != st.session_state.master_notes:
            st.session_state.master_notes = updated_notes
            if "notes_pdf_bytes" in st.session_state:
                del st.session_state.notes_pdf_bytes
            st.rerun()

    with tab_preview:
        st.markdown("---")
        if st.session_state.master_notes.strip():
            # Use the existing function to render Markdown + Diagrams
            display_response_with_diagrams(st.session_state.master_notes)
        else:
            st.info("Your notes are empty. Start typing in Edit mode or append responses from the chat.")
