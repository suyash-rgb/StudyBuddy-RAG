import logging
import streamlit as st
from dotenv import load_dotenv

# Configure application logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables from .env file at application startup
load_dotenv()

# Configure page layout and style
st.set_page_config(
    page_title="StudyBuddy - Academic Study Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Postponed imports to allow loading variables and page config first
from core.database import get_qdrant_client
from core.session import init_session_state
from ui.styling import inject_custom_css
from ui.sidebar import render_sidebar
from ui.chat import render_chat_interface
from ui.editor import render_notes_editor

# Inject Custom CSS (including right-aligned chat styling)
inject_custom_css()

# Initialize Session State
init_session_state()

# Main application header
st.title("📚 StudyBuddy")
st.subheader("Lightweight Academic Study Assistant")

# Initialize database client
client = None
try:
    logger.info("Attempting to initialize Qdrant database client...")
    client = get_qdrant_client()
except Exception as e:
    logger.error(f"Failed to initialize local Qdrant client: {e}")
    st.error(f"Failed to initialize local Qdrant client: {e}")

# Render UI Components
render_sidebar(client)

# Layout State: 0 (Chat Only), 1 (Split), 2 (Notes Only)
layout_state = st.session_state.get("layout_state", 0)

if layout_state == 0:
    col_chat, col_toggle = st.columns([1, 0.04])
    with col_toggle:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("❮", help="Open Notes Workspace", key="open_notes", use_container_width=True):
            st.session_state.layout_state = 1
            st.rerun()
            
    with col_chat:
        render_chat_interface(client)

elif layout_state == 1:
    col_chat, col_toggle, col_notes = st.columns([1, 0.06, 1])
    with col_toggle:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("❯", help="Close Notes", key="close_notes", use_container_width=True):
            st.session_state.layout_state = 0
            st.rerun()
        if st.button("❮", help="Expand Notes to Full Width", key="expand_notes_full", use_container_width=True):
            st.session_state.layout_state = 2
            st.rerun()
            
    with col_chat:
        render_chat_interface(client)
    with col_notes:
        render_notes_editor()

elif layout_state == 2:
    col_toggle, col_notes = st.columns([0.04, 1])
    with col_toggle:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("❯", help="Show Chat", key="show_chat", use_container_width=True):
            st.session_state.layout_state = 1
            st.rerun()
            
    with col_notes:
        render_notes_editor()
