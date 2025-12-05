import os
import json
import shutil
from groq import Groq
from langchain_community.vectorstores import Chroma
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document

class AudioAgent:
    def __init__(self, groq_api_key, persistence_base_dir="data/audio_vector_stores"):
        self.groq_api_key = groq_api_key
        self.client = Groq(api_key=groq_api_key)
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.1-8b-instant")
        self.persistence_base_dir = persistence_base_dir
        self.chat_history_store = {}
        
        # Ensure base directory exists
        os.makedirs(self.persistence_base_dir, exist_ok=True)

    def _get_session_dir(self, session_id):
        return os.path.join(self.persistence_base_dir, session_id)

    def _get_metadata_path(self, session_id):
        return os.path.join(self._get_session_dir(session_id), "metadata.json")

    def get_uploaded_files(self, session_id):
        """Returns a list of uploaded audio filenames for the session."""
        metadata_path = self._get_metadata_path(session_id)
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f).get("files", [])
        return []

    def _add_file_to_metadata(self, session_id, filename):
        """Adds a filename to the session metadata."""
        session_dir = self._get_session_dir(session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        metadata_path = self._get_metadata_path(session_id)
        files = []
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                files = json.load(f).get("files", [])
        
        if filename not in files:
            files.append(filename)
            with open(metadata_path, "w") as f:
                json.dump({"files": files}, f)
        
        return len(files)

    def process_audio(self, audio_path, session_id, original_filename, language_mode="Auto-Detect Language"):
        """Processes an audio file, transcribes it, and adds it to the session's vector store."""
        current_files = self.get_uploaded_files(session_id)
        
        if original_filename in current_files:
             return -2 # Already uploaded
             
        if len(current_files) >= 5:
            return -1 # Limit reached

        # Transcribe
        try:
            with open(audio_path, "rb") as file:
                # 1. Universal Translation (Any Audio -> English Text)
                if language_mode == "Universal Translate -> English":
                    transcription = self.client.audio.translations.create(
                        file=(original_filename, file.read()),
                        model="whisper-large-v3",
                        response_format="json",
                        temperature=0.0 
                    )
                
                # 2. Specific or Auto Transcription
                else:
                    # Map UI selection to ISO codes
                    lang_map = {
                        "Force English (Transcription)": "en",
                        "Force Arabic (Transcription)": "ar",
                        "Force French (Transcription)": "fr",
                        "Force Spanish (Transcription)": "es"
                    }
                    selected_iso = lang_map.get(language_mode) # Returns None for "Auto-Detect"
                    
                    transcription = self.client.audio.transcriptions.create(
                        file=(original_filename, file.read()),
                        model="whisper-large-v3",
                        response_format="json",
                        language=selected_iso, 
                        temperature=0.0
                    )

                text_content = transcription.text
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return 0

        if not text_content:
            return 0

        # Create Document
        doc = Document(
            page_content=text_content,
            metadata={"source": original_filename}
        )
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=5000, chunk_overlap=200)
        splits = text_splitter.split_documents([doc])
        
        if not splits:
            return 0
        
        persist_dir = self._get_session_dir(session_id)
        
        vectorstore = Chroma.from_documents(
            documents=splits, 
            embedding=self.embeddings,
            persist_directory=persist_dir
        )
        
        self._add_file_to_metadata(session_id, original_filename)
        return len(splits)

    def clear_context(self, session_id):
        """Clears the context for a specific session."""
        session_dir = self._get_session_dir(session_id)
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                print(f"Error deleting session directory: {e}")
        
        if session_id in self.chat_history_store:
            del self.chat_history_store[session_id]

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.chat_history_store:
            self.chat_history_store[session_id] = ChatMessageHistory()
        return self.chat_history_store[session_id]

    def get_response(self, user_input, session_id):
        persist_dir = self._get_session_dir(session_id)
        
        # Check if vectorstore exists for this session
        if not os.path.exists(persist_dir) or not os.listdir(persist_dir):
            return "Please upload an audio file first."
            
        vectorstore = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)

        retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
        
        # Contextualize question prompt
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, contextualize_q_prompt
        )

        # Answer prompt
        system_prompt = (
            "You are an intelligent assistant analyzing audio transcripts. "
            "The text provided below in the 'Context' section IS the actual content of the audio files you need to use. "
            "Use this context to answer the user's question. "
            "If the user asks for a summary, summarize the provided context. "
            "If the answer is not in the context, state that you cannot find the information in the audio."
            "\n\n"
            "Context from Audio:\n{context}"
        )
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])

        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        rag_chain = create_retrieval_chain(
            history_aware_retriever, question_answer_chain
        )

        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer"
        )

        response = conversational_rag_chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}}
        )
        
        return response['answer']
