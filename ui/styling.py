import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');
        
        /* Use a serif font for headings (academic) and Inter for body text */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3 {
            font-family: 'Lora', serif !important;
        }
        
        /* Academic subtle styling */
        .stButton>button {
            border-radius: 6px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease-in-out !important;
            width: 100%;
            margin-top: 10px;
        }
        .stButton>button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* Chat message separation */
        .stChatMessage {
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid var(--secondary-background-color);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        /* Right-align user chat messages */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            display: flex;
            flex-direction: row-reverse;
            align-items: end;
            background-color: var(--secondary-background-color);
        }
        
        /* Ensure the text inside the user message is also right-aligned */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stMarkdownContainer"] {
            text-align: right;
        }
        
        /* Hide the scrollbar in the sidebar but maintain positioning */
        [data-testid="stSidebar"] ::-webkit-scrollbar {
            display: none;
        }
        [data-testid="stSidebar"] {
            -ms-overflow-style: none;
            scrollbar-width: none;
        }
    </style>
    """, unsafe_allow_html=True)
