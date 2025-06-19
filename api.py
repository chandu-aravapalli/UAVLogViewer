from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict
from chatbot import (
    chatbot_pipeline, setup_rag_chain, load_and_embed_docs, ConversationState, check_environment
)
import os
from dotenv import load_dotenv
import logging
import shutil

# Load environment variables
load_dotenv()
check_environment()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG components ONCE at startup
DEFAULT_DOC_PATH = os.getenv("MAVLINK_DOC_PATH", "/Users/chandu/Arena/backend/structured_message_logs.txt")
retriever = load_and_embed_docs(DEFAULT_DOC_PATH)
qa_chain, llm = setup_rag_chain(retriever)

# Store conversation states for different sessions
conversation_states: Dict[str, ConversationState] = {}

UPLOAD_DIR = "./uploaded_logs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatMessage(BaseModel):
    session_id: str = Field(..., alias='sessionId')
    message: str
    bin_path: str = Field(None, alias='binPath')

class ChatResponse(BaseModel):
    response: str
    error: str = None

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    try:
        # Get or create conversation state for this session
        if chat_message.session_id not in conversation_states:
            conversation_states[chat_message.session_id] = ConversationState(
                history=[],
                current_context={}
            )
        conversation_state = conversation_states[chat_message.session_id]

        # Require bin_path from frontend, do not use default
        bin_path = chat_message.bin_path
        if not bin_path:
            logging.getLogger(__name__).error("No bin_path provided in request.")
            return ChatResponse(response="", error="No .bin file path provided. Please upload a log file in the sidebar.")

        logging.getLogger(__name__).info(f"API using bin_path: {bin_path}")

        # Call the pipeline
        response = chatbot_pipeline(
            user_question=chat_message.message,
            bin_path=bin_path,
            retriever=retriever,
            qa_chain=qa_chain,
            llm=llm,
            conversation_state=conversation_state
        )
        return ChatResponse(response=response)
    except Exception as e:
        logging.getLogger(__name__).error(f"API error: {str(e)}")
        return ChatResponse(response="", error=str(e))

@app.post("/api/upload_bin")
async def upload_bin(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"binPath": file_location}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 