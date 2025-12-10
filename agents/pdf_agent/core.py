import os
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter  # ✅ Fixed import
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage
import shutil

class PDFAgent:
    def __init__(self, groq_api_key):
        self.llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama-3.3-70b-versatile", temperature=0)
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_stores = {}
        self.chat_histories = {}
        self.uploaded_files = {}

    def process_pdf(self, pdf_path, session_id):
        """Process PDF and create vector store"""
        try:
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            
            persist_directory = f"data/pdf_vector_stores/{session_id}"
            os.makedirs(persist_directory, exist_ok=True)
            
            vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=self.embeddings,
                persist_directory=persist_directory
            )
            
            self.vector_stores[session_id] = vectorstore
            
            filename = os.path.basename(pdf_path)
            if session_id not in self.uploaded_files:
                self.uploaded_files[session_id] = []
            self.uploaded_files[session_id].append(filename)
            
            return f"✅ PDF '{filename}' processed successfully! You can now ask questions about it."
        
        except Exception as e:
            return f"❌ Error processing PDF: {e}"

    def process_pdf_with_name(self, pdf_path, session_id, original_filename):
        """Process PDF with original filename tracking"""
        try:
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)
            
            persist_directory = f"data/pdf_vector_stores/{session_id}"
            os.makedirs(persist_directory, exist_ok=True)
            
            if session_id in self.vector_stores:
                self.vector_stores[session_id].add_documents(splits)
            else:
                vectorstore = Chroma.from_documents(
                    documents=splits,
                    embedding=self.embeddings,
                    persist_directory=persist_directory
                )
                self.vector_stores[session_id] = vectorstore
            
            if session_id not in self.uploaded_files:
                self.uploaded_files[session_id] = []
            if original_filename not in self.uploaded_files[session_id]:
                self.uploaded_files[session_id].append(original_filename)
            
            return f"✅ PDF '{original_filename}' processed successfully!"
        
        except Exception as e:
            return f"❌ Error processing PDF: {e}"

    def get_uploaded_pdfs(self, session_id):
        """Return list of uploaded PDFs for the session"""
        return self.uploaded_files.get(session_id, [])

    def format_docs(self, docs):
        """Format documents for context"""
        return "\n\n".join(doc.page_content for doc in docs)

    def get_response(self, query, session_id):
        """Get response based on PDF content"""
        if session_id not in self.vector_stores:
            return "⚠️ No PDF uploaded yet. Please upload a PDF first."
        
        try:
            vectorstore = self.vector_stores[session_id]
            retriever = vectorstore.as_retriever()
            
            if session_id not in self.chat_histories:
                self.chat_histories[session_id] = []
            
            template = """Answer the question based only on the following context:
{context}

Question: {question}

Answer: """
            
            prompt = ChatPromptTemplate.from_template(template)
            
            rag_chain = (
                {"context": retriever | self.format_docs, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            response = rag_chain.invoke(query)
            
            self.chat_histories[session_id].append(HumanMessage(content=query))
            self.chat_histories[session_id].append(AIMessage(content=response))
            
            return response
        
        except Exception as e:
            return f"❌ Error generating response: {e}"

    def clear_context(self, session_id):
        """Clear the vector store and chat history for a session"""
        if session_id in self.vector_stores:
            del self.vector_stores[session_id]
        
        if session_id in self.chat_histories:
            del self.chat_histories[session_id]
        
        if session_id in self.uploaded_files:
            del self.uploaded_files[session_id]
        
        persist_directory = f"data/pdf_vector_stores/{session_id}"
        if os.path.exists(persist_directory):
            try:
                shutil.rmtree(persist_directory)
            except Exception as e:
                print(f"Warning: Could not delete directory {persist_directory}: {e}")