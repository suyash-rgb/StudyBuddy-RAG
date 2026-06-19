import streamlit as st

def init_session_state():
    """Initializes the required session state variables if they do not exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "indexed_files" not in st.session_state:
        st.session_state.indexed_files = []
    if "awaiting_diagram_confirmation" not in st.session_state:
        st.session_state.awaiting_diagram_confirmation = False
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None
    if "pending_selected_file" not in st.session_state:
        st.session_state.pending_selected_file = None
    if "diagram_confirmation_choice" not in st.session_state:
        st.session_state.diagram_confirmation_choice = None

def get_messages():
    """Returns the current list of chat messages."""
    return st.session_state.messages

def add_message(role: str, content: str, **kwargs):
    """Appends a new message to the chat history."""
    msg = {"role": role, "content": content}
    msg.update(kwargs)
    st.session_state.messages.append(msg)
    # Invalidate cached PDF export bytes so it must be regenerated
    if "pdf_bytes" in st.session_state:
        del st.session_state.pdf_bytes

def clear_messages():
    """Clears the chat history from the session state."""
    st.session_state.messages = []
    if "pdf_bytes" in st.session_state:
        del st.session_state.pdf_bytes

def get_indexed_files():
    return st.session_state.get("indexed_files", [])

def add_indexed_file(filename: str):
    if "indexed_files" not in st.session_state:
        st.session_state.indexed_files = []
    if filename not in st.session_state.indexed_files:
        st.session_state.indexed_files.append(filename)

def clear_indexed_files():
    st.session_state.indexed_files = []
