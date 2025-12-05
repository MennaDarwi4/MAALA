import streamlit as st
import os
import tempfile
from agents.ocr_agent.core import OCRAgent

def ocr_view(orchestrator, session_id):
    st.markdown("""
        <style>
        .ocr-header {
            text-align: center;
            padding: 2rem;
            border: 2px dashed #ccc;
            border-radius: 1rem;
            margin-bottom: 2rem;
            background: #fafafa;
        }
        .ocr-title {
            font-size: 2rem;
            font-weight: 700;
            color: #333;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="ocr-header">
            <div class="ocr-title">🖼️ Optical Character Recognition</div>
            <p>Upload an image to extract text instantly</p>
        </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
            
        with col2:
            if st.button("Extract Text", type="primary", use_container_width=True):
                with st.spinner("Extracting text..."):
                    try:
                        # Save to temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        try:
                            ocr_agent = OCRAgent(groq_api_key=os.getenv("GROQ_API_KEY"))
                            text = ocr_agent.extract_text(tmp_path)
                            
                            st.markdown("### 📝 Extracted Text")
                            st.text_area("Result", text, height=300)
                            
                            # Add to chat history so it's saved
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"**Extracted Text from {uploaded_file.name}:**\n\n{text}"
                            })
                            
                        finally:
                            os.remove(tmp_path)
                            
                    except Exception as e:
                        st.error(f"Error processing image: {e}")
