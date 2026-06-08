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
    page_title="PdfInsight - Academic Study Assistant",
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

# Inject Custom CSS (including right-aligned chat styling)
inject_custom_css()

# Initialize Session State
init_session_state()

# Main application header
st.title("📚 PdfInsight")
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
render_chat_interface(client)
