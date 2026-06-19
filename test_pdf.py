import sys
import os

# Add the project directory to the python path
sys.path.append(os.path.abspath("."))

from core.export import export_conversation_to_pdf
from core.session import init_session_state, add_message

class MockSessionState(dict):
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value

import streamlit as st
st.session_state = MockSessionState()
init_session_state()

add_message("user", "What is the process?")
add_message("assistant", "Here is the process:\n\n```mermaid\ngraph TD\nA-->B\n```\nAnd it finishes.")

try:
    from core.export import replace_diagrams_with_images_for_pdf
    import logging
    logging.basicConfig(level=logging.INFO)
    temp_files = []
    text = "Here is the process:\n\n```mermaid\ngraph TD\nA-->B\n```\nAnd it finishes."
    res = replace_diagrams_with_images_for_pdf(text, temp_files)
    print("REPLACED TEXT RESULT:")
    print(res)
    print("TEMP FILES:", temp_files)
    
    pdf_bytes = export_conversation_to_pdf()
    print("Success, PDF size:", len(pdf_bytes))
    with open("test_output.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("Wrote test_output.pdf")
except Exception as e:
    import traceback
    traceback.print_exc()
