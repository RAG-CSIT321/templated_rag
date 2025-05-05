from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os
import json
import logging
import threading
import redis
from datetime import datetime

from file_processor import FileProcessor
from query_engine import QueryEngine
from chat_history import ChatHistory
from store_data import StoreData
from watcher import MySQLWatcher

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates setup
templates = Jinja2Templates(directory="templates")

# MySQL Configuration
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'rag_database'),
    'port': int(os.getenv('MYSQL_PORT', 3306))
}

# Initialize components
query_engine = QueryEngine()
file_processor = FileProcessor(data_dir="data")
chat_history = ChatHistory(history_file="chat_history.json")
store_data = StoreData()
mysql_watcher = MySQLWatcher(MYSQL_CONFIG)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main chat UI"""
    return templates.TemplateResponse("chat_ui.html", {"request": request})

@app.post("/api/interact_with_agent")
async def interact_with_agent(request: Request):
    """
    API endpoint to interact with the RAG system.
    It first checks if data is available in Redis before querying the LLM.
    """
    data = await request.json()
    prompt = data.get("prompt", "")
    session_id = data.get("session_id", "default")

    # Check if retriever is initialized
    if file_processor.retriever is None:
        return JSONResponse(
            content={"messages": [{"role": "assistant", "content": "Please upload a file before asking questions."}]},
            status_code=400
        )

    try:
        use_context = True  # Now we definitely have retriever
        response = query_engine.query(file_processor.retriever, prompt, use_context=use_context)

        # Process LLM response
        if hasattr(response, "content"):
            response_content = response.content
        elif isinstance(response, dict):
            response_content = json.dumps(response, indent=2)
        else:
            response_content = str(response)

        if not isinstance(response_content, str) or not response_content.strip():
            response_content = "I don't know. Please upload relevant files to provide more context."

    except Exception as e:
        logger.error(f"Error in QueryEngine: {e}")
        raise HTTPException(status_code=500, detail=f"Query Engine Error: {str(e)}")

    # Save to chat history
    chat_history.save_chat_history(session_id, [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response_content}
    ])
    return JSONResponse(content={"messages": [{"role": "assistant", "content": response_content}]})

@app.options("/api/interact_with_agent")
async def handle_options():
    """Handle OPTIONS requests for CORS"""
    return JSONResponse(content={})

@app.post("/api/upload_file")
async def upload_file(file: UploadFile = File(...)):
    """
    API endpoint for uploading files.
    After upload, the file is processed and indexed in Redis.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    # Save file to data directory
    file_path = os.path.join("data", file.filename)
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        result = file_processor.process_file(file_path)
        return JSONResponse(content={"message": result, "status": "success"})
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/list_chat_sessions")
async def list_chat_sessions():
    """List available chat sessions."""
    sessions = chat_history.list_chat_sessions()
    return JSONResponse(content={"sessions": sessions})

@app.get("/api/load_chat_history/{session_id}")
async def load_chat_history(session_id: str):
    """Load chat history for a given session."""
    history = chat_history.load_chat_history(session_id)
    if history:
        return JSONResponse(content=history)
    else:
        raise HTTPException(status_code=404, detail="No history found")

### Background Services ###
def redis_listener():
    """
    Background thread that listens for embedding update requests.
    When an update is received, it re-processes the text and stores the new embedding in Redis.
    """
    logger.info("[📡] Starting Redis listener...")
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0))
    )
    pubsub = redis_client.pubsub()
    pubsub.subscribe("embedding_updates")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
            logger.info(f"[📥] Redis received embedding update: {data}")
            
            text = data["text"]
            key = data["key"]
            metadata = data.get("metadata", {})

            # Store new embedding in Redis
            store_data.store_single_embedding_to_redis(text, key, metadata)
            logger.info("[✅] Embedding stored in Redis.")

        except Exception as e:
            logger.error(f"[❌] Error processing Redis message: {e}")

@app.on_event("startup")
async def startup_event():
    """Start background services when FastAPI starts."""
    try:
        # Start Redis listener
        threading.Thread(target=redis_listener, daemon=True).start()
        
        # Start MySQL watcher
        threading.Thread(target=mysql_watcher.run, daemon=True).start()
        
        logger.info("✅ All background services started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start background services: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        reload=os.getenv('RELOAD', 'false').lower() == 'true'
    )


