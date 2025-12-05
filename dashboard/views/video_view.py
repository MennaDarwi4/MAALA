import streamlit as st
import os
from agents.video_agent import VideoAgent

def video_view(orchestrator, session_id):
    st.markdown("""
        <style>
        .video-container {
            background: #000;
            color: white;
            padding: 2rem;
            border-radius: 1rem;
            text-align: center;
            margin-bottom: 2rem;
        }
        .video-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #FF0000;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="video-container">
            <div class="video-title">🎥 Video Summarizer</div>
            <p>Get instant summaries from YouTube videos</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    
    with col1:
        video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        
        if st.button("Summarize Video", type="primary", use_container_width=True):
            if video_url:
                with st.spinner("Fetching transcript and summarizing..."):
                    try:
                        # Initialize VideoAgent
                        video_agent = VideoAgent(groq_api_key=os.getenv("GROQ_API_KEY"))
                        summary = video_agent.summarize(video_url)
                        
                        st.session_state.current_video_summary = summary
                        st.session_state.current_video_url = video_url
                        
                    except Exception as e:
                        st.error(f"Error processing video: {e}")
            else:
                st.warning("Please enter a valid URL.")

    # Display Result
    if 'current_video_summary' in st.session_state:
        st.divider()
        
        # Embed video
        if 'current_video_url' in st.session_state:
            st.video(st.session_state.current_video_url)
            
        st.markdown("### 📝 Summary")
        st.write(st.session_state.current_video_summary)
