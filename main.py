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
chat_history = ChatHistory(history_file="chat_history.json")
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
    session_id = data.get('session_id', 'default')

    try:
        use_context = file_processor.retriever is not None
        response = query_engine.query(file_processor.retriever, prompt, use_context=use_context)
        # Get actual content
        if hasattr(response, "content"):
            response_content = response.content
        elif isinstance(response, dict):
            response_content = json.dumps(response, indent=2)
        else:
            response_content = str(response)

        if not isinstance(response_content, str) or not response_content.strip():
            response_content = "I don't know. Please upload relevant files to provide more context."

    except Exception as e:
        logging.error(f"Error in QueryEngine: {e}")
        raise HTTPException(status_code=500, detail=f"Query Engine Error: {str(e)}")

    chat_history.save_chat_history(session_id, [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response_content}
    ])
    return JSONResponse(content={"messages": [{"role": "assistant", "content": response_content}]})

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

@app.get("/api/list_chat_sessions")
async def list_chat_sessions():
    sessions = chat_history.list_chat_sessions()
    return JSONResponse(content=sessions)

@app.get("/api/load_chat_history/{session_id}")
async def load_chat_history(session_id: str):
    history = chat_history.load_chat_history(session_id)
    if history:
        return JSONResponse(content=history)
    else:
        raise HTTPException(status_code=404, detail="No history found")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        reload=os.getenv('RELOAD', 'false').lower() == 'true'
    )


