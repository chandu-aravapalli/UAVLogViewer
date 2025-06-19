# MAVLink RAG Chatbot

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI
from pymavlink import mavutil
import json
import os
import logging
from dotenv import load_dotenv
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from langchain.schema import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Set your default paths here
DEFAULT_DOC_PATH = "/Users/chandu/Arena/backend/structured_message_logs.txt"

@dataclass
class ConversationState:
    """Maintains the state of the conversation."""
    history: List[Dict[str, str]]  # List of {role: str, content: str} pairs
    current_context: Dict[str, any]  # Current context including message types, structures, etc.
    last_question: Optional[str] = None
    last_answer: Optional[str] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    
    def add_interaction(self, role: str, content: str):
        """Add an interaction to the conversation history."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_recent_context(self, n: int = 3) -> str:
        """Get the n most recent interactions as context."""
        recent = self.history[-n:] if len(self.history) > n else self.history
        return "\n".join([f"{item['role']}: {item['content']}" for item in recent])
    
    def needs_clarification(self, question: str) -> bool:
        """Determine if clarification is needed for the current question."""
        clarification_prompt = f"""
        Based on the conversation history and the current question, determine if clarification is needed.
        
        Conversation History:
        {self.get_recent_context()}
        
        Current Question: {question}
        
        Consider:
        1. Is the question ambiguous or unclear?
        2. Are there multiple possible interpretations?
        3. Is additional context needed to provide a meaningful answer?
        
        Return a JSON object:
        {{
            "needs_clarification": true/false,
            "clarification_question": "What specific aspect would you like to know about...",
            "reason": "Brief explanation of why clarification is needed"
        }}
        """
        try:
            llm = OpenAI(temperature=0)
            response = llm.invoke(clarification_prompt)
            try:
                # Extract JSON object from response using regex
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    result = json.loads(json_str)
                    self.clarification_needed = result.get("needs_clarification", False)
                    self.clarification_question = result.get("clarification_question", None)
                    return self.clarification_needed
                else:
                    logger.error(f"Clarification LLM did not return valid JSON: {response}")
                    self.clarification_needed = False
                    self.clarification_question = None
                    return False
            except json.JSONDecodeError:
                logger.error(f"Clarification LLM did not return valid JSON: {response}")
                self.clarification_needed = False
                self.clarification_question = None
                return False
        except Exception as e:
            logger.error(f"Error in clarification check: {str(e)}")
            self.clarification_needed = False
            self.clarification_question = None
            return False

def check_environment():
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Please set your OpenAI API key as an environment variable: OPENAI_API_KEY")

# ---------- Step 1: Load and Embed MAVLink Documentation ----------
def load_and_embed_docs(doc_path):
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"MAVLink documentation file not found at: {doc_path}")
    
    loader = TextLoader(doc_path)
    docs = loader.load()
    # Split on double newlines (blank lines)
    raw_text = docs[0].page_content if hasattr(docs[0], 'page_content') else docs[0]
    sections = [section.strip() for section in raw_text.split('\n\n') if section.strip()]
    # Convert each section to a Document object
    section_docs = [Document(page_content=section) for section in sections]
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(section_docs, embeddings)
    return vectorstore.as_retriever()

# ---------- Step 2: Setup Clarifying RAG Chain ----------
def setup_rag_chain(retriever):
    llm = OpenAI(temperature=0)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True
    )
    return qa_chain, llm

# ---------- Step 3: Extract Message Structure from RAG ----------
def extract_message_structure(chunks, message_type):
    """Extract the message structure from RAG chunks."""
    structure = {}
    for chunk in chunks:
        content = chunk.page_content
        if message_type in content:
            try:
                # Split content into lines
                lines = content.split('\n')
                for line in lines:
                    # Skip empty lines and lines without colons
                    if ':' not in line:
                        continue
                    
                    # Parse field information
                    # Format: field_name: type (unit) - description
                    parts = line.split(':', 1)
                    if len(parts) != 2:
                        continue
                        
                    field_name = parts[0].strip()
                    field_info = parts[1].strip()
                    
                    # Extract type, unit, and description
                    type_info = field_info.split('(')[0].strip()
                    unit = None
                    description = None
                    
                    if '(' in field_info and ')' in field_info:
                        unit = field_info.split('(')[1].split(')')[0].strip()
                        if '-' in field_info:
                            description = field_info.split('-', 1)[1].strip()
                    elif '-' in field_info:
                        description = field_info.split('-', 1)[1].strip()
                    
                    # Store field information
                    structure[field_name] = {
                        'type': type_info,
                        'unit': unit,
                        'description': description
                    }
                
                if structure:
                    break
                    
            except Exception as e:
                logger.error(f"Error parsing message structure: {str(e)}")
                continue
    
    if not structure:
        logger.warning(f"No structure found for message type {message_type}")
    return structure

# ---------- Step 4: Extract Data from .bin File ----------
def extract_from_bin(bin_path, message_type, structure):
    """Extract data from .bin file using the message structure."""
    if not os.path.exists(bin_path):
        raise FileNotFoundError(f"MAVLink .bin file not found at: {bin_path}")
    
    mav = mavutil.mavlink_connection(bin_path)
    messages = []
    total_messages = 0
    message_types_found = set()  # Track all message types we find
    
    try:
        while True:
            msg = mav.recv_match()
            if msg is None:
                break
                
            total_messages += 1
            msg_type = msg.get_type()
            message_types_found.add(msg_type)
            
            if msg_type.lower() == message_type.lower():
                # Convert message to dictionary
                msg_dict = msg.to_dict()
                
                # Add documentation info to each field if available
                enhanced_msg = {}
                for field_name, value in msg_dict.items():
                    field_info = {
                        'value': value
                    }
                    # Add documentation if available
                    if field_name in structure:
                        field_info.update({
                            'unit': structure[field_name].get('unit'),
                            'description': structure[field_name].get('description')
                        })
                    enhanced_msg[field_name] = field_info
                
                messages.append(enhanced_msg)
                    
    except Exception as e:
        logger.error(f"Error reading MAVLink messages: {str(e)}")
    
    if not messages:
        logger.warning(f"No messages found of type {message_type}")
        logger.info("Available message types that might contain acceleration data:")
        for msg_type in message_types_found:
            if any(acc_term in msg_type.lower() for acc_term in ['acc', 'imu', 'raw']):
                logger.info(f"- {msg_type}")
    
    return messages

# ---------- Step 5: RAG Chatbot Pipeline ----------
def chatbot_pipeline(user_question: str, bin_path: str, retriever, qa_chain, llm, conversation_state: ConversationState) -> str:
    conversation_state.add_interaction("user", user_question)

    if conversation_state.needs_clarification(user_question):
        conversation_state.add_interaction("assistant", conversation_state.clarification_question)
        return conversation_state.clarification_question

    if not conversation_state.current_context.get("retrieved_chunks"):
        rag_output = qa_chain.invoke({"query": user_question})
        conversation_state.current_context["retrieved_chunks"] = [doc.page_content for doc in rag_output['source_documents']]
    else:
        rag_output = {"source_documents": [type('Doc', (object,), {"page_content": chunk}) for chunk in conversation_state.current_context["retrieved_chunks"]]}

    # Always determine the message type for each question
    message_type_prompt = f"""
You are a MAVLink expert.
The user asked: \"{user_question}\"
Here are the relevant documentation chunks:
{chr(10).join([f'Chunk {i+1}:{chr(10)}{doc.page_content}' for i, doc in enumerate(rag_output['source_documents'])])}
Based on these chunks, identify the most relevant MAVLink message type for answering this question.
IMPORTANT:
1. You must ONLY use message types that are explicitly defined in these chunks.
2. For acceleration data, if you see \"ACC\" in the documentation, you should also consider \"IMU\" messages.
3. For each message type you suggest, also provide the field names that contain the relevant data.
Return in JSON format:
{{
    "message_type": "XXX",
    "alternative_types": ["YYY", "ZZZ"],
    "relevant_fields": ["field1", "field2"]
}}
If no relevant message type is found in the chunks, return:
{{"message_type": null}}
    """
    query_plan = llm.invoke(message_type_prompt)
    try:
        query_dict = json.loads(query_plan.strip())
        message_type = query_dict['message_type']
        if message_type is None:
            response = "I couldn't find any relevant message types in the documentation for your question."
            conversation_state.add_interaction("assistant", response)
            return response
        conversation_state.current_context.update({
            "message_type": message_type,
            "alternative_types": query_dict.get('alternative_types', []),
            "relevant_fields": query_dict.get('relevant_fields', [])
        })
    except Exception as e:
        logger.error(f"Error parsing message type: {str(e)}")
        response = "I couldn't determine which MAVLink message type to analyze."
        conversation_state.add_interaction("assistant", response)
        return response

    message_type = conversation_state.current_context["message_type"]
    message_structure = conversation_state.current_context.get("message_structure")
    if not message_structure:
        message_structure = extract_message_structure(rag_output['source_documents'], message_type)
        if not message_structure:
            for alt_type in conversation_state.current_context.get("alternative_types", []):
                alt_structure = extract_message_structure(rag_output['source_documents'], alt_type)
                if alt_structure:
                    message_type = alt_type
                    message_structure = alt_structure
                    break
            if not message_structure:
                response = f"I couldn't find the structure for {message_type} messages."
                conversation_state.add_interaction("assistant", response)
                return response
        conversation_state.current_context["message_structure"] = message_structure

    # Always extract messages for the current message type for each question
    messages = extract_from_bin(bin_path, message_type, message_structure)
    if not messages:
        for alt_type in conversation_state.current_context.get("alternative_types", []):
            messages = extract_from_bin(bin_path, alt_type, message_structure)
            if messages:
                message_type = alt_type
                break
    if not messages:
        response = f"I couldn't find any {message_type} messages in the log file."
        conversation_state.add_interaction("assistant", response)
        return response

    messages = messages[:5]  # Limit to 5 messages for the final prompt
    final_prompt = f"""
You are an aviation data analyst.
The user asked: \"{user_question}\"
I have analyzed the {message_type} messages from the flight data. Here is what I found:
{json.dumps(messages, indent=2)}
Please provide a direct, concise answer to the user's question. Focus only on the relevant information and avoid technical details unless specifically asked.
    """
    final_answer = llm.invoke(final_prompt)
    conversation_state.add_interaction("assistant", final_answer)
    return final_answer

# ---------- Example Usage ----------
if __name__ == "__main__":
    try:
        # Check environment
        check_environment()
        
        # Get file paths from user, use defaults if input is empty
        doc_path = input(f"Enter path to MAVLink documentation file [{DEFAULT_DOC_PATH}]: ").strip() or DEFAULT_DOC_PATH
        bin_path = input(f"Enter path to MAVLink .bin file [{DEFAULT_BIN_PATH}]: ").strip() or DEFAULT_BIN_PATH
        
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"MAVLink documentation file not found at: {doc_path}")
        if not os.path.exists(bin_path):
            raise FileNotFoundError(f"MAVLink .bin file not found at: {bin_path}")
        
        # Load retriever and chains
        retriever = load_and_embed_docs(doc_path)
        qa_chain, llm = setup_rag_chain(retriever)

        # Initialize conversation state
        conversation_state = ConversationState(
            history=[],
            current_context={}
        )

        # Interactive question answering
        print("\nChatbot is ready! Type 'quit' to exit.")
        while True:
            question = input("\nEnter your question: ").strip()
            if question.lower() == 'quit':
                break
                
            print("\nProcessing your question...")
            answer = chatbot_pipeline(question, bin_path, retriever, qa_chain, llm, conversation_state)
            print("\nAnswer:\n", answer)
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"\nError: {str(e)}")
