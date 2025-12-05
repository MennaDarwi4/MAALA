import sys
import os

# Add the project root to sys.path to allow imports from agents
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.pdf_agent.core import PDFAgent
from agents.search_agent.core import SearchAgent
from agents.audio_agent.core import AudioAgent

class OrchestratorAgent:
    def __init__(self, groq_api_key):
        self.pdf_agent = PDFAgent(groq_api_key)
        self.search_agent = SearchAgent(groq_api_key)
        self.audio_agent = AudioAgent(groq_api_key)
        self.context = {"has_pdf": False}

    def process_pdf(self, pdf_path, session_id, original_filename=None):
        """Delegates PDF processing to PDFAgent"""
        if original_filename:
            return self.pdf_agent.process_pdf_with_name(pdf_path, session_id, original_filename)
        return self.pdf_agent.process_pdf(pdf_path, session_id)

    def process_audio(self, audio_path, session_id, original_filename, language_mode="Auto-Detect Language"):
        """Delegates Audio processing to AudioAgent"""
        return self.audio_agent.process_audio(audio_path, session_id, original_filename, language_mode)

    def get_uploaded_pdfs(self, session_id):
        """Returns list of uploaded PDFs for the session"""
        return self.pdf_agent.get_uploaded_pdfs(session_id)

    def get_uploaded_audio_files(self, session_id):
        """Returns list of uploaded audio files for the session"""
        return self.audio_agent.get_uploaded_files(session_id)

    def clear_context(self, session_id):
        """Clears the context of the agents for a specific session"""
        self.pdf_agent.clear_context(session_id)
        self.audio_agent.clear_context(session_id)
        # self.context["has_pdf"] = False # Context is now per session in PDF agent

    def route_query(self, query, session_id, agent_type="Auto"):
        """
        Routes the query to the appropriate agent based on agent_type.
        """
        
        if agent_type == "PDF Agent":
            response = self.pdf_agent.get_response(query, session_id)
            return {"response": response, "source": "PDF Agent"}
            
        elif agent_type == "Audio Agent":
            response = self.audio_agent.get_response(query, session_id)
            return {"response": response, "source": "Audio Agent"}

        elif agent_type == "Search Agent":
            result = self.search_agent.run(query)
            if isinstance(result, dict):
                return {
                    "response": result["response"], 
                    "source": "Search Agent", 
                    "sources": result.get("sources", []),
                    "history": result.get("history", [])
                }
            else:
                return {"response": result, "source": "Search Agent", "sources": []}
                
        else: # Auto / Legacy
            # Check if session has PDFs
            uploaded_pdfs = self.get_uploaded_pdfs(session_id)
            uploaded_audio = self.get_uploaded_audio_files(session_id)
            
            if uploaded_pdfs:
                response = self.pdf_agent.get_response(query, session_id)
                
                # Fallback logic
                fallback_phrases = [
                    "cannot find the information", 
                    "not in the context", 
                    "doesn't mention", 
                    "not answerable", 
                    "no information in the provided context",
                    "does not contain information",
                    "context does not provide",
                    "i don't have the pdf",
                    "i do not have the pdf"
                ]
                if any(phrase in response.lower() for phrase in fallback_phrases):
                    # Fallback to Search Agent
                    result = self.search_agent.run(query)
                    if isinstance(result, dict):
                        return {
                            "response": result["response"], 
                            "source": "Search Agent", 
                            "sources": result.get("sources", []),
                            "history": result.get("history", []),
                            "note": "PDF Agent could not answer, fell back to Search Agent."
                        }
                    else:
                        return {"response": result, "source": "Search Agent", "sources": []}
    
                return {"response": response, "source": "PDF Agent"}
            
            elif uploaded_audio:
                 response = self.audio_agent.get_response(query, session_id)
                 return {"response": response, "source": "Audio Agent"}

            else:
                result = self.search_agent.run(query)
                if isinstance(result, dict):
                    return {
                        "response": result["response"], 
                        "source": "Search Agent", 
                        "sources": result.get("sources", []),
                        "history": result.get("history", [])
                    }
                else:
                    return {"response": result, "source": "Search Agent", "sources": []}
