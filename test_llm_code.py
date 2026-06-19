from core.session import init_session_state, get_messages
import streamlit as st
class MockSessionState(dict):
    def __getattr__(self, key): return self[key]
    def __setattr__(self, key, value): self[key] = value
st.session_state = MockSessionState()
init_session_state()
msgs = get_messages()
for m in msgs:
    if m['role'] == 'assistant':
        print('---')
        print(m['content'][-1000:])
