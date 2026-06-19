import sys
import os

# Add the project directory to the python path
sys.path.append(os.path.abspath("."))

from core.export import export_conversation_to_pdf
from core.session import init_session_state, add_message

# Mock the session state for testing outside of Streamlit
import streamlit as st
st.session_state = {}
init_session_state()

add_message("user", "What is the process?")
add_message("assistant", "Here is the process:\n\n```mermaid\ngraph TD\nA-->B\n```\nAnd it finishes.")

try:
    pdf_bytes = export_conversation_to_pdf()
    print("Success, PDF size:", len(pdf_bytes))
except Exception as e:
    import traceback
    traceback.print_exc()
