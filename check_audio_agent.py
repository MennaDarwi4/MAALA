try:
    from agents.audio_agent.core import AudioAgent
    print("AudioAgent imported successfully.")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
