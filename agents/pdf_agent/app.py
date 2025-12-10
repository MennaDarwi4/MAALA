import streamlit as st
import os
import sys
import tempfile
from dotenv import load_dotenv

# ✅ أضف المسار للـ path عشان يلاقي core.py
sys.path.insert(0, os.path.dirname(__file__))

from core import PDFAgent

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

st.set_page_config(page_title="PDF Agent Test UI", layout="wide")

st.title("MAALA - PDF Agent Test UI")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Try to get key from env
    env_api_key = os.getenv("GROQ_API_KEY")
    
    if env_api_key:
        st.success("API Key loaded from environment")
        api_key = env_api_key
    else:
        api_key = st.text_input("Enter Groq API Key", type="password")
    
    session_id = st.text_input("Session ID", value="default_session")

if not api_key:
    st.warning("Please enter your Groq API Key to proceed.")
    st.stop()

# Initialize Agent
if 'pdf_agent' not in st.session_state:
    st.session_state.pdf_agent = PDFAgent(api_key)

# File Upload
st.header("1. Upload PDF")
uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if st.button("Process PDFs"):
        with st.spinner("Processing PDFs..."):
            for uploaded_file in uploaded_files:
                # Save to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Process
                try:
                    num_splits = st.session_state.pdf_agent.process_pdf(tmp_path)
                    st.success(f"Processed {uploaded_file.name} ({num_splits} chunks)")
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {e}")
                finally:
                    os.remove(tmp_path)

# Chat Interface
st.header("2. Chat with PDF")

# Display chat history
history = st.session_state.pdf_agent.get_session_history(session_id)
for msg in history.messages:
    st.chat_message(msg.type).write(msg.content)

# User Input
if prompt := st.chat_input("Ask a question about the PDF..."):
    st.chat_message("human").write(prompt)
    
    with st.spinner("Thinking..."):
        try:
            response = st.session_state.pdf_agent.get_response(prompt, session_id)
            st.chat_message("ai").write(response)
        except Exception as e:
            st.error(f"Error generating response: {e}")