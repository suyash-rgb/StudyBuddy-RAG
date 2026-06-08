import streamlit as st

def init_session_state():
    """Initializes the required session state variables if they do not exist."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

def get_messages():
    """Returns the current list of chat messages."""
    return st.session_state.messages

def add_message(role: str, content: str, references: list = None):
    """Appends a new message to the session state."""
    msg = {"role": role, "content": content}
    if references:
        msg["references"] = references
    st.session_state.messages.append(msg)

def clear_messages():
    """Clears the chat history from the session state."""
    st.session_state.messages = []
