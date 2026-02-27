import os
import logging
import io
import uuid # <-- Make sure this is imported
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import nest_asyncio

# Apply asyncio patch
nest_asyncio.apply()
load_dotenv()

# --- Import Your Refactored Logic ---
from src.config import Config
from src.pdf_processing import PDFProcessor
from src.embeddings import EmbeddingSelector
from src.conversation import ConversationEnhancer
from src.notes_manager import PersistentStorageManager
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import LlamaCpp
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, AIMessage

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# --- Vectorstore Directory ---
VECTORSTORE_DIR = "vectorstores"
os.makedirs(VECTORSTORE_DIR, exist_ok=True)
# ---

# --- Single, App-Wide Instances ---
try:
    config_loader = Config()
    app_settings = config_loader.get_app_settings()
    if not config_loader.validate_settings(app_settings):
        logger.warning("Configuration validation failed. Check .env file.")
    
    pdf_processor = PDFProcessor(app_settings)
    embedding_selector = EmbeddingSelector()
    conversation_enhancer = ConversationEnhancer()
    storage_manager = PersistentStorageManager() # Initialized once
    
    CHUNK_SIZE = app_settings.get("chunk_size", 1000)
    CHUNK_OVERLAP = app_settings.get("chunk_overlap", 200)

except Exception as e:
    logger.critical(f"Failed to initialize application modules: {e}", exc_info=True)
    raise

# --- In-Memory Session Cache ---
active_sessions = {}

def get_llm_instance(model_selection: str, custom_api_key: str = None):
    """
    Helper function to initialize LLM based on selection.
    """
    try:
        if "Google" in model_selection:
            google_api_key = custom_api_key if custom_api_key else os.getenv("GOOGLE_API_KEY")
            
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in .env and no custom key provided.")
            
            model_map = {
                "Google (Gemini 2.5 Flash)": "gemini-2.5-flash",
            }
            model_id = model_map.get(model_selection, "gemini-2.5-flash")
            
            return ChatGoogleGenerativeAI(
                model=model_id,
                google_api_key=google_api_key,
                temperature=0.1,
                convert_system_message_to_human=True
            )
        
        elif "Local" in model_selection:
            model_path = app_settings.get('model_path')
            if not model_path or not os.path.exists(model_path):
                raise ValueError(f"Model file not found: {model_path}. Check MODEL_PATH in .env.")
            
            return LlamaCpp(
                model_path=model_path,
                temperature=0.1, n_ctx=4096, n_batch=512, n_gpu_layers=0,
                stop=["<end_of_turn>", "<eos>"], verbose=True,
            )
        else:
            raise ValueError(f"Unknown model selection: {model_selection}")
            
    except Exception as e:
        logger.error(f"Failed to initialize LLM '{model_selection}': {e}")
        return None

# =========== Frontend Route ===========

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

# =========== API Routes ===========

@app.route('/api/sessions', methods=['GET'])
def get_all_sessions():
    """Get all saved chat session titles and IDs."""
    try:
        sessions = storage_manager.get_all_chat_sessions()
        return jsonify(sessions)
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}", exc_info=True)
        return jsonify({"error": "Could not retrieve sessions"}), 500

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """Get the full chat history for one session AND load it into memory."""
    try:
        session_data = storage_manager.get_chat_session(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404
        
        if session_id in active_sessions:
            logger.info(f"Session {session_id} is already active.")
        else:
            logger.info(f"Loading session {session_id} into memory...")
            vectorstore_path = session_data.get('vectorstore_path')
            
            if not vectorstore_path or not os.path.exists(vectorstore_path):
                logger.warning(f"No vectorstore found for session {session_id}.")
                return jsonify(session_data)

            try:
                embedding_model = embedding_selector.get_embedding_model()
                vectorstore = FAISS.load_local(
                    vectorstore_path, 
                    embedding_model,
                    allow_dangerous_deserialization=True 
                )
                
                model_selection = "Google (Gemini 2.5 Flash)"
                if "Local" in session_data.get('title', ''):
                     model_selection = "Local (Gemma 2 2B)"

                llm = get_llm_instance(model_selection, custom_api_key=None)
                if not llm:
                    logger.error(f"Failed to load LLM {model_selection} for session {session_id}")
                    return jsonify(session_data)

                model_type_slug = 'local' if 'Local' in model_selection else 'google'
                
                conversation_chain = conversation_enhancer.get_conversation_chain(
                    vectorstore=vectorstore,
                    llm=llm,
                    model_type=model_type_slug
                )
                
                active_sessions[session_id] = {
                    "vectorstore": vectorstore,
                    "conversation": conversation_chain
                }
                logger.info(f"Successfully loaded session {session_id} into active memory.")
                
            except Exception as e:
                logger.error(f"Failed to load session {session_id} from disk: {e}", exc_info=True)
        
        return jsonify(session_data)
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Could not retrieve session"}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Deletes a chat session."""
    try:
        session_data = storage_manager.get_chat_session(session_id)
        if session_data:
            vectorstore_path = session_data.get('vectorstore_path')
            if vectorstore_path and os.path.exists(vectorstore_path):
                try:
                    os.remove(vectorstore_path)
                    logger.info(f"Deleted vectorstore file: {vectorstore_path}")
                except Exception as e:
                    logger.warning(f"Could not delete vectorstore file {vectorstore_path}: {e}")

        if session_id in active_sessions:
            del active_sessions[session_id]
        
        success = storage_manager.delete_chat_session(session_id)
        if not success:
            return jsonify({"error": "Session not found or could not be deleted"}), 404
            
        return jsonify({"message": "Session deleted successfully"})
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Could not delete session"}), 500

# --- THIS IS THE NEW ROUTE YOU ARE MISSING ---
@app.route('/api/sessions/<session_id>/title', methods=['PUT'])
def rename_session(session_id: str):
    """
    Updates the title of a chat session.
    """
    data = request.json
    new_title = data.get('title')

    if not new_title:
        return jsonify({"error": "No title provided"}), 400
    
    try:
        success = storage_manager.rename_chat_session(session_id, new_title)
        if not success:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify({"message": "Title updated successfully", "new_title": new_title})
    except Exception as e:
        logger.error(f"Failed to rename session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Could not rename session"}), 500
# --- END OF NEW ROUTE ---

@app.route('/api/process', methods=['POST'])
def process_documents():
    """Upload PDFs, create vectorstore, and initialize conversation chain."""
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
    
    files = request.files.getlist('files')
    model_selection = request.form.get('model', 'Google (Gemini 2.5 Flash)')
    session_id = request.form.get('session_id', None)
    if session_id == 'null': session_id = None
    
    custom_api_key = request.form.get('custom_api_key', None)
    if custom_api_key == 'null' or custom_api_key == '':
        custom_api_key = None

    if not files or all(f.filename == '' for f in files):
        return jsonify({"error": "No files selected"}), 400
    
    try:
        raw_text, metadata = pdf_processor.extract_pdf_text(files)
        if not raw_text:
            return jsonify({"error": "No text could be extracted from the documents."}), 400
        
        text_chunks = pdf_processor.get_text_chunks(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
        
        embedding_model = embedding_selector.get_embedding_model()
        vectorstore = embedding_selector.create_vectorstore(text_chunks, embedding_model)
        
        vectorstore_path = None
        if session_id:
            session_data = storage_manager.get_chat_session(session_id)
            if session_data:
                vectorstore_path = session_data.get('vectorstore_path')
        
        if not vectorstore_path:
            vectorstore_filename = f"{str(uuid.uuid4())}.faiss"
            vectorstore_path = os.path.join(VECTORSTORE_DIR, vectorstore_filename)
            
        vectorstore.save_local(vectorstore_path)
        logger.info(f"Vectorstore saved to {vectorstore_path}")

        llm = get_llm_instance(model_selection, custom_api_key=custom_api_key)
        if not llm:
            return jsonify({"error": f"Failed to load model: {model_selection}"}), 500

        session_title = f"Chat with {', '.join(f.filename for f in files)[:50]}..."
        if session_id:
            session_data = storage_manager.get_chat_session(session_id)
            if session_data:
                session_title = session_data.get('title', session_title)
        
        model_type_slug = 'local' if 'Local' in model_selection else 'google'
        
        conversation_chain = conversation_enhancer.get_conversation_chain(
            vectorstore=vectorstore,
            llm=llm,
            model_type=model_type_slug
        )
        
        file_names = [f.filename for f in files]
        session_id = storage_manager.save_chat_session(
            session_id=session_id,
            title=session_title,
            chat_history=[],
            uploaded_files=file_names,
            vectorstore_path=vectorstore_path
        )

        active_sessions[session_id] = {
            "vectorstore": vectorstore,
            "conversation": conversation_chain
        }
        
        return jsonify({
            "message": f"Documents processed! Chatting with {model_selection}.",
            "session_id": session_id,
            "title": session_title,
            "uploaded_files": file_names
        })

    except Exception as e:
        logger.error(f"Error during document processing: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle a user's chat message."""
    data = request.json
    session_id = data.get('session_id')
    user_query = data.get('query')

    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400
    if not session_id:
        return jsonify({"error": "No session ID provided"}), 400
    
    if session_id not in active_sessions:
        logger.warning(f"Session {session_id} not in active cache. Attempting to load...")
        get_session(session_id)
        
        if session_id not in active_sessions:
            return jsonify({"error": "Chat session not found or failed to load. Please upload documents again."}), 400

    try:
        conversation_chain = active_sessions[session_id]['conversation']
        
        session_data = storage_manager.get_chat_session(session_id)
        chat_history_dicts = session_data.get('chat_history', [])
        
        converted_chat_history = []
        for msg in chat_history_dicts:
            if msg['role'] == 'user':
                converted_chat_history.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'bot':
                converted_chat_history.append(AIMessage(content=msg['content']))
        
        response = conversation_chain.invoke({
            'input': user_query,
            'chat_history': converted_chat_history
        })
        
        bot_response_content = response.get('answer', "I'm sorry, I couldn't process that.")

        user_message = {"role": "user", "content": user_query, "timestamp": str(datetime.now())}
        bot_message = {"role": "bot", "content": bot_response_content, "timestamp": str(datetime.now())}
        
        chat_history_dicts.extend([user_message, bot_message])

        title = session_data.get('title', 'New Chat')
        if len(chat_history_dicts) < 3:
            title = user_query[:50]

        storage_manager.save_chat_session(
            session_id=session_id,
            title=title,
            chat_history=chat_history_dicts,
            uploaded_files=session_data.get('uploaded_files', []),
            vectorstore_path=session_data.get('vectorstore_path')
        )

        return jsonify(bot_message)

    except Exception as e:
        logger.error(f"Error during chat invocation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/sessions/<session_id>/download_csv', methods=['GET'])
def download_chat_csv(session_id: str):
    """Downloads the chat history as a CSV file."""
    try:
        session_data = storage_manager.get_chat_session(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404
        
        chat_history = session_data.get('chat_history', [])
        if not chat_history:
            return jsonify({"error": "No chat history to download"}), 400

        csv_data = pdf_processor.save_chat_history(chat_history)
        if csv_data is None:
            return jsonify({"error": "No chat history to save"}), 400

        return send_file(
            io.BytesIO(csv_data.encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"chat_history_{session_id[:8]}.csv"
        )
    except Exception as e:
        logger.error(f"Failed to generate CSV for session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Could not generate CSV"}), 500


# =========== Run the App ===========
if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
