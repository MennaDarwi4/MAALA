import inspect
import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.core import OrchestratorAgent
from dashboard.session_manager import SessionManager

# Import Views
from dashboard.views.search_view import search_view
from dashboard.views.pdf_view import pdf_view
from dashboard.views.audio_view import audio_view
from dashboard.views.video_view import video_view
from dashboard.views.ocr_view import ocr_view

# ✅ FIX: Load .env from project root (not dashboard folder)
# project_root = Path(__file__).parent.parent
# env_path = project_root / '.env'
# load_dotenv(dotenv_path=env_path)

load_dotenv()

# Load from Streamlit secrets if available (for cloud deployment)
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

# --- START: الجزء المُضاف لفرض بداية جديدة عند إعادة تحميل التطبيق ---
# Force fresh start on app reload
if 'app_started' not in st.session_state:
    st.session_state.app_started = True

    # Initialize Session Manager first if it's not initialized (needed for the next steps)
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()

    # Create a new session
    new_session_id = st.session_state.session_manager.create_new_session()
    st.session_state.current_session_id = new_session_id
    default_msgs = [{"role": "assistant", "content": "Hi! How can I help you today?"}]

    # Get current mode
    mode = "🔍 Search Agent"  # Default mode

    st.session_state.session_manager.save_session(
        new_session_id,
        default_msgs,
        "New Session",
        agent_type=mode
    )
    st.session_state.messages = default_msgs
# --- END: الجزء المُضاف ---

st.set_page_config(page_title="MAALA", page_icon="🤖", layout="wide")

# Load Custom CSS
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Please ensure dashboard/style.css exists.")

load_css("dashboard/style.css")

# Initialize Session Manager
if 'session_manager' not in st.session_state:
    st.session_state.session_manager = SessionManager()
else:
    # Hot-reload fix for SessionManager
    try:
        sig = inspect.signature(st.session_state.session_manager.list_sessions)
        if 'agent_type' not in sig.parameters:
            del st.session_state.session_manager
            st.rerun()
    except Exception:
        del st.session_state.session_manager
        st.rerun()

# Initialize Orchestrator
if 'orchestrator' not in st.session_state:
    env_api_key = os.getenv("GROQ_API_KEY")
    if not env_api_key:
        st.error("❌ GROQ_API_KEY not found in environment variables.")
        # Note: env_path is commented out in original code, so this line might raise an error if uncommented
        # st.info(f"📁 Looking for .env file at: {env_path}")
        st.info(f"🔑 Current API Key value: {env_api_key}")
        st.warning("Please create a .env file in the project root with: GROQ_API_KEY=your_key_here")
        st.stop()
    st.session_state.orchestrator = OrchestratorAgent(env_api_key)
else:
    # Hot-reload fix
    try:
        sig_clear = inspect.signature(st.session_state.orchestrator.clear_context)
        sig_route = inspect.signature(st.session_state.orchestrator.route_query)
        if 'session_id' not in sig_clear.parameters or 'agent_type' not in sig_route.parameters:
            del st.session_state.orchestrator
            st.rerun()
    except Exception:
        del st.session_state.orchestrator
        st.rerun()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=50)
    st.title("MAALA")
    
    mode = st.radio(
        "Select Agent", 
        ["🔍 Search Agent", "📄 PDF Agent", "🎙️ Audio Agent", "🎥 Video Summarizer", "🖼️ OCR Agent"],
        key="agent_mode",
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.subheader("History")
    
    if st.button("➕ New Chat", use_container_width=True):
        new_session_id = st.session_state.session_manager.create_new_session()
        st.session_state.current_session_id = new_session_id
        default_msgs = [{"role": "assistant", "content": "Hi! How can I help you today?"}]
        st.session_state.session_manager.save_session(
            new_session_id, 
            default_msgs, 
            "New Session", 
            agent_type=mode
        )
        st.session_state.messages = default_msgs
        
        if 'orchestrator' in st.session_state:
            st.session_state.orchestrator.clear_context(new_session_id)
        st.rerun()

    # List sessions filtered by current mode
    sessions = st.session_state.session_manager.list_sessions(agent_type=mode)
    
    if 'current_session_id' not in st.session_state:
        if sessions:
            st.session_state.current_session_id = sessions[0]["id"]
        else:
            new_id = st.session_state.session_manager.create_new_session()
            st.session_state.current_session_id = new_id
            st.session_state.session_manager.save_session(
                new_id, 
                [{"role": "assistant", "content": "Hi! How can I help you today?"}], 
                "New Session", 
                agent_type=mode
            )

    # Ensure current session is valid for this mode
    current_sess_exists = any(s["id"] == st.session_state.current_session_id for s in sessions)
    if not current_sess_exists and sessions:
        st.session_state.current_session_id = sessions[0]["id"]
    elif not current_sess_exists and not sessions:
        new_id = st.session_state.session_manager.create_new_session()
        st.session_state.current_session_id = new_id
        st.session_state.session_manager.save_session(
            new_id, 
            [{"role": "assistant", "content": "Hi! How can I help you today?"}], 
            "New Session", 
            agent_type=mode
        )
        st.rerun()

    for session in sessions:
        if st.button(
            session['name'], 
            key=session["id"], 
            type="secondary" if session["id"] != st.session_state.current_session_id else "primary", 
            use_container_width=True
        ):
            st.session_state.current_session_id = session["id"]
            st.rerun()

# Load Session Data
current_session = st.session_state.session_manager.load_session(st.session_state.current_session_id)
if current_session:
    # Check if this is an old session with no recent activity
    loaded_messages = current_session.get("messages", [])
    
    # If session only has the default message, it's effectively new
    if len(loaded_messages) <= 1:
        st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I help you today?"}]
    else:
        st.session_state.messages = loaded_messages
else:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! How can I help you today?"}]

# Main Content Router
if mode == "🔍 Search Agent":
    search_view(st.session_state.orchestrator, st.session_state.current_session_id)
elif mode == "📄 PDF Agent":
    pdf_view(st.session_state.orchestrator, st.session_state.current_session_id)
elif mode == "🎙️ Audio Agent":
    audio_view(st.session_state.orchestrator, st.session_state.current_session_id)
elif mode == "🎥 Video Summarizer":
    video_view(st.session_state.orchestrator, st.session_state.current_session_id)
elif mode == "🖼️ OCR Agent":
    ocr_view(st.session_state.orchestrator, st.session_state.current_session_id)

# Update Session Name Logic (Global)
if len(st.session_state.messages) > 1:
    current_sess_data = st.session_state.session_manager.load_session(st.session_state.current_session_id)
    if not current_sess_data or current_sess_data.get("name") == "New Session":
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                new_name = msg["content"][:30] + "..." if len(msg["content"]) > 30 else msg["content"]
                st.session_state.session_manager.save_session(
                    st.session_state.current_session_id, 
                    st.session_state.messages, 
                    new_name,
                    agent_type=mode
                )
                break
    else:
        st.session_state.session_manager.save_session(
            st.session_state.current_session_id, 
            st.session_state.messages,
            agent_type=mode
        )