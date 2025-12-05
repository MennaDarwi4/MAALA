import streamlit as st
import os
import tempfile

def audio_view(orchestrator, session_id):
    st.markdown("""
        <style>
        .audio-header {
            background: linear-gradient(90deg, #1A237E 0%, #3949AB 100%);
            padding: 2rem;
            border-radius: 1rem;
            color: white;
            margin-bottom: 2rem;
        }
        .audio-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .audio-subtitle {
            opacity: 0.8;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="audio-header">
            <div class="audio-title">🎙️ Audio Intelligence</div>
            <div class="audio-subtitle">Transcribe, Translate, and Chat with Audio</div>
        </div>
    """, unsafe_allow_html=True)

    # Settings
    with st.expander("⚙️ Transcription Settings"):
        language_mode = st.selectbox(
            "Language Mode",
            options=[
                "Auto-Detect Language",
                "Force English (Transcription)",
                "Force Arabic (Transcription)",
                "Force French (Transcription)",
                "Force Spanish (Transcription)",
                "Universal Translate -> English"
            ],
            index=0
        )

    # Upload Area
    uploaded_audio = orchestrator.get_uploaded_audio_files(session_id)
    
    if not uploaded_audio:
        st.info("Upload an audio file to begin.")
        
    with st.expander("➕ Upload Audio", expanded=not uploaded_audio):
        uploaded_files = st.file_uploader("Upload Audio files", type=["mp3", "mp4", "wav", "m4a"], accept_multiple_files=True)
        if uploaded_files:
            if st.button("Process Audio", type="primary"):
                with st.spinner("Transcribing audio..."):
                    for uploaded_file in uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = tmp_file.name
                        
                        try:
                            result = orchestrator.process_audio(
                                tmp_path, 
                                session_id, 
                                original_filename=uploaded_file.name,
                                language_mode=language_mode
                            )
                            
                            if result > 0:
                                st.success(f"✅ Processed {uploaded_file.name}")
                            else:
                                st.warning(f"⚠️ Issue processing {uploaded_file.name}")
                                
                        except Exception as e:
                            st.error(f"Error: {e}")
                        finally:
                            if os.path.exists(tmp_path):
                                os.remove(tmp_path)
                    st.rerun()

    if uploaded_audio:
        st.markdown("### 🎧 Active Audio")
        for audio in uploaded_audio:
            st.markdown(f"- {audio}")

    # Chat
    if uploaded_audio:
        st.divider()
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        if prompt := st.chat_input("Ask about the audio...", key="audio_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        result = orchestrator.route_query(
                            prompt, 
                            session_id,
                            agent_type="Audio Agent"
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
