import streamlit as st

def init_session_state():
    """Initializes the required session state variables if they do not exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "indexed_files" not in st.session_state:
        st.session_state.indexed_files = []

def get_messages():
    """Returns the current list of chat messages."""
    return st.session_state.messages

def add_message(role: str, content: str, **kwargs):
    """Appends a new message to the chat history."""
    msg = {"role": role, "content": content}
    msg.update(kwargs)
    st.session_state.messages.append(msg)

def clear_messages():
    """Clears the chat history from the session state."""
    st.session_state.messages = []

def get_indexed_files():
    return st.session_state.get("indexed_files", [])

def add_indexed_file(filename: str):
    if "indexed_files" not in st.session_state:
        st.session_state.indexed_files = []
    if filename not in st.session_state.indexed_files:
        st.session_state.indexed_files.append(filename)

def clear_indexed_files():
    st.session_state.indexed_files = []
