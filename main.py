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
from chat_history_mysql import ChatHistoryMySQL
from store_data import StoreData

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



# Initialize components
query_engine = QueryEngine()
file_processor = FileProcessor(data_dir="data")
chat_history = ChatHistoryMySQL()
store_data = StoreData()
store_data.store_mysql()
file_processor.retriever = store_data.load_retriever()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main chat UI"""
    return templates.TemplateResponse("chat_ui.html", {"request": request})

@app.post("/api/interact_with_agent")
async def interact_with_agent(request: Request):
    data = await request.json()
    prompt = data.get('prompt', '')
    session_id = data.get('session_id')
    user_id = data.get('user_id')

    if not user_id or not session_id:
        raise HTTPException(status_code=400, detail="User ID and Session ID are required")
    
    try:
        # Save user message (appends to existing messages)
        chat_history.save_chat_message(user_id, session_id, 'user', prompt)
        
        use_context = file_processor.retriever is not None
        response = query_engine.query(file_processor.retriever, prompt, use_context=use_context)
        
        # Get response content
        response_content = response.content if hasattr(response, "content") else str(response)
        if not response_content.strip():
            response_content = "I don't know. Please upload relevant files to provide more context."

        # Save assistant response (appends to existing messages)
        chat_history.save_chat_message(user_id, session_id, 'assistant', response_content)
        
        return JSONResponse(content={
            "messages": [{"role": "assistant", "content": response_content}],
            "session_id": session_id
        })
    except Exception as e:
        logging.error(f"Error in QueryEngine: {e}")
        raise HTTPException(status_code=500, detail=f"Query Engine Error: {str(e)}")

@app.options("/api/interact_with_agent")
async def handle_options():
    return JSONResponse(content={})

@app.post("/api/upload_file")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    file_path = os.path.join("data", file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    result = file_processor.process_file(file_path)
    return JSONResponse(content={"message": result})

# Add these new endpoints:

@app.post("/api/create_new_session/{user_id}")
async def create_new_session(user_id: str):
    """Create a new chat session for the user"""
    session_id = chat_history.create_new_session(user_id)
    return JSONResponse(content={
        "status": "success",
        "session_id": session_id
    })

'''
@app.post("/api/save_message")
async def save_message(request: Request):
    """Save a single message to a session"""
    data = await request.json()
    user_id = data.get('user_id')
    session_id = data.get('session_id')
    role = data.get('role')
    content = data.get('content')
    
    if not all([user_id, session_id, role, content]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    try:
        chat_history.save_message(user_id, session_id, role, content)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''

@app.get("/api/list_chat_sessions/{user_id}")
async def list_chat_sessions(user_id: str):
    sessions = chat_history.list_user_sessions(user_id)
    # Convert to list of dictionaries if not already
    if sessions and isinstance(sessions[0], tuple):
        sessions = [{
            "session_id": session[0],
            "session_name": session[1],
            "last_updated": session[2]
        } for session in sessions]
    
    return JSONResponse(content={
        "status": "success",
        "data": sessions  # Consistent array format
    })
@app.delete("/api/delete_session/{user_id}/{session_id}")
async def delete_session(user_id: str, session_id: str):
    success = chat_history.delete_session(user_id, session_id)
    if success:
        return JSONResponse(content={"status": "success"})
    else:
        raise HTTPException(status_code=404, detail="Session not found or not owned by user")

# Remove the default session creation from load_chat_history endpoint
@app.get("/api/load_chat_history/{user_id}/{session_id}")
async def load_chat_history(user_id: str, session_id: str):
    history = chat_history.load_chat_history(user_id, session_id)
    if history:
        return JSONResponse(content=history)
    else:
        raise HTTPException(status_code=404, detail="Session not found")

# Add session name to create endpoint
@app.post("/api/create_new_session/{user_id}")
async def create_new_session(user_id: str, request: Request):
    """Create a new chat session for the user"""
    data = await request.json()
    session_name = data.get('session_name', None)
    session_id = chat_history.create_new_session(user_id, session_name)
    return JSONResponse(content={
        "status": "success",
        "session_id": session_id,
        "session_name": session_name or f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
    })
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        reload=os.getenv('RELOAD', 'false').lower() == 'true'
    )


