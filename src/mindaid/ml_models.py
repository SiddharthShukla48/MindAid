"""
Machine Learning models for diagnosis and counseling
"""

import os
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging

logger = logging.getLogger(__name__)

# Global variables
diagnosis_model = None
tokenizer = None
vector_store = None
llm = None
store = {}

def load_diagnosis_model():
    """Load the BERT diagnosis model"""
    global diagnosis_model, tokenizer

    try:
        model_path = os.getenv("DIAGNOSIS_MODEL_PATH", "SiddharthShukla48/MindAid_Diagnosis_bert-base-multilingual-cased")

        logger.info("Loading diagnosis model...")
        diagnosis_model = AutoModelForSequenceClassification.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        logger.info("Diagnosis model loaded successfully")
        return diagnosis_model, tokenizer

    except Exception as e:
        logger.error(f"Failed to load diagnosis model: {e}")
        raise

def load_vector_store():
    """Load the vector store for counseling"""
    global vector_store, llm

    try:
        # Option 1: Use OpenAI embeddings (if you have OpenAI API key)
        # from langchain_openai import OpenAIEmbeddings
        # embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

        # Option 2: Use HuggingFace embeddings (free, no API key needed)
        from transformers import AutoTokenizer, AutoModel
        import torch
        import numpy as np
        from langchain.embeddings.base import Embeddings

        class HuggingFaceEmbeddingsWrapper(Embeddings):
            def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModel.from_pretrained(model_name)
                self.device = torch.device('cpu')

            def embed_documents(self, texts):
                embeddings = []
                for text in texts:
                    inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                        embeddings.append(embedding)
                return embeddings

            def embed_query(self, text):
                inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                return embedding

        embeddings = HuggingFaceEmbeddingsWrapper()

        # Option 3: Use Google Generative AI embeddings (requires API key)
        # from langchain_google_genai import GoogleGenerativeAIEmbeddings
        # embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        # Load documents
        loader = PyPDFDirectoryLoader("context_for_RAG/")
        docs = loader.load()

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        final_documents = text_splitter.split_documents(docs[:20])

        # Create vector store
        vector_store = FAISS.from_documents(final_documents, embeddings)

        # Initialize LLM
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")

        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-70b-8192"
        )

        logger.info("Vector store and LLM loaded successfully")
        return vector_store

    except Exception as e:
        logger.error(f"Failed to load vector store: {e}")
        raise

def predict_disorder(user_input: str) -> str:
    """Predict mental health disorder from user input"""
    global diagnosis_model, tokenizer

    if not diagnosis_model or not tokenizer:
        raise ValueError("Diagnosis model not loaded")

    try:
        # Tokenize input
        inputs = tokenizer(user_input, return_tensors="pt", padding=True, truncation=True)

        # Get predictions
        outputs = diagnosis_model(**inputs)
        logits = outputs.logits

        # Get predicted class
        max_index = torch.argmax(logits, dim=-1).item()
        class_labels = ["Addiction", "Anxiety", "Depression", "PTSD"]

        return class_labels[max_index]

    except Exception as e:
        logger.error(f"Error in disorder prediction: {e}")
        raise

def get_counseling_response(user_input: str, session_id: str = "default") -> str:
    """Get counseling response using RAG"""
    global vector_store, llm, store

    if not vector_store or not llm:
        raise ValueError("Counseling models not loaded")

    try:
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
            ("human", "{input}"),
        ])

        # Counseling system prompt
        system_prompt = (
            "Assume you are a mental health counselor, learn from the counselling technique and sample conversation given to you "
            "and ask the patient the right questions about their situation."
            "If you don't know the answer, say that you don't know."
            "Use two sentences maximum and keep the answer concise."
            "When you feel that the patient is satisfied, end the conversation."
            "Counselling technique and sample conversation: {context}"
        )

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        # Create retriever and chains
        retriever = vector_store.as_retriever()
        history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

        # Session management
        def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]

        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

        # Get response
        response = conversational_rag_chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
        )

        return response['answer']

    except Exception as e:
        logger.error(f"Error in counseling response: {e}")
        raise
