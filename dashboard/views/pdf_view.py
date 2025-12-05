import streamlit as st
import os
import tempfile

def pdf_view(orchestrator, session_id):
    st.markdown("""
        <style>
        .pdf-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 0;
            border-bottom: 1px solid #eee;
            margin-bottom: 2rem;
        }
        .pdf-title {
            font-size: 2rem;
            font-weight: 700;
            color: #D32F2F;
        }
        .pdf-stat {
            background: #FFEBEE;
            color: #D32F2F;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.875rem;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    uploaded_pdfs = orchestrator.get_uploaded_pdfs(session_id)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"""
            <div class="pdf-header">
                <div class="pdf-title">📄 Document Analysis</div>
                <div class="pdf-stat">{len(uploaded_pdfs)} Active Files</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Sidebar-like area for PDF management (using columns for layout)
    with st.expander("📂 Manage Documents", expanded=not uploaded_pdfs):
        uploaded_files = st.file_uploader("Upload PDF files (Max 5 total)", type="pdf", accept_multiple_files=True)
        if uploaded_files:
            if st.button("Process Files", type="primary"):
                with st.spinner("Processing PDFs..."):
                    for uploaded_file in uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        try:
                            result = orchestrator.process_pdf(
                                tmp_path, 
                                session_id, 
                                original_filename=uploaded_file.name
                            )
                            
                            if result == -1:
                                st.error(f"❌ Limit reached! Cannot add {uploaded_file.name}.")
                            elif result == -2:
                                st.info(f"ℹ️ {uploaded_file.name} is already uploaded.")
                            elif result == 0:
                                st.warning(f"⚠️ Processed {uploaded_file.name} but found no text.")
                            else:
                                st.success(f"✅ Added {uploaded_file.name}")
                                
                        except Exception as e:
                            st.error(f"Error processing {uploaded_file.name}: {e}")
                        finally:
                            os.remove(tmp_path)
                    st.rerun()
        
        if uploaded_pdfs:
            st.markdown("### Active Files")
            for pdf in uploaded_pdfs:
                st.markdown(f"- 📄 {pdf}")

    # Chat Interface
    if not uploaded_pdfs:
        st.info("👆 Upload a PDF document to start analyzing.")
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("Ask about your documents...", key="pdf_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing documents..."):
                    try:
                        result = orchestrator.route_query(
                            prompt, 
                            session_id,
                            agent_type="PDF Agent"
                        )
                        
                        response_text = result["response"]
                        
                        st.write(response_text)
                        
                        st.session_state.messages.append({
                            'role': 'assistant', 
                            "content": response_text
                        })
                        
                        st.session_state.session_manager.save_session(
                            session_id, 
                            st.session_state.messages
                        )
                        
                    except Exception as e:
                        st.error(f"Error: {e}")
