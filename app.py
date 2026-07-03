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

# Notes Panel Toggle Logic
notes_open = st.session_state.get("notes_open", True)

if notes_open:
    col1, col_toggle, col2 = st.columns([1, 0.04, 1])
    with col_toggle:
        # Push the button down slightly to align with content
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("❯", help="Collapse Notes Workspace", key="collapse_notes"):
            st.session_state.notes_open = False
            st.rerun()
            
    with col1:
        render_chat_interface(client)
    with col2:
        render_notes_editor()
else:
    col1, col_toggle = st.columns([1, 0.04])
    with col_toggle:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("❮", help="Expand Notes Workspace", key="expand_notes"):
            st.session_state.notes_open = True
            st.rerun()
            
    # When closed, chat takes full width (minus the small toggle column)
    with col1:
        render_chat_interface(client)
