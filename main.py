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
from mysql_listener import MySQLChangeListener

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth_service import AuthService, SECRET_KEY, ALGORITHM
from fastapi import Depends, HTTPException
from pydantic import BaseModel
# Define a model for the request body
class SaveMessageRequest(BaseModel):
    user_id: str
    session_id: str
    role: str
    content: str
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth_service = AuthService()

@app.post("/api/register")
async def register_user(
    request: Request  # Add this to accept raw JSON
):
    data = await request.json()  # Get JSON data
    try:
        result = auth_service.register_user(
            data.get('username'),
            data.get('password'),
            data.get('email')
        )
        return JSONResponse(content=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/token")
async def login_for_access_token(request: Request):
    try:
        # Log the raw request body for debugging
        body = await request.body()
        logger.info(f"Received login request body: {body}")
        
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")
            
        try:
            data = await request.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
            
        logger.info(f"Attempting login for user: {username}")
        return auth_service.authenticate_user(username, password)
    except HTTPException as e:
        logger.error(f"HTTP Exception in login: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in login: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    return auth_service.get_current_user(token)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main chat UI"""
    return templates.TemplateResponse("chat_ui.html", {"request": request})

@app.post("/api/interact_with_agent")
async def interact_with_agent(request: Request, token: str = Depends(oauth2_scheme)):
    current_user = auth_service.get_current_user(token)
    data = await request.json()
    prompt = data.get('prompt', '')
    session_id = data.get('session_id')
    user_id = current_user['user_id']

    if not user_id or not session_id:
        raise HTTPException(status_code=400, detail="User ID and Session ID are required")
    
    try:
        # Save user message (appends to existing messages)
        # chat_history.save_chat_message(user_id, session_id, 'user', prompt)
        
        use_context = file_processor.retriever is not None
        response = query_engine.query(file_processor.retriever, prompt, use_context=use_context)
        
        # Get response content
        response_content = response.content if hasattr(response, "content") else str(response)
        if not response_content.strip():
            response_content = "I don't know. Please upload relevant files to provide more context."

        # Save assistant response (appends to existing messages)
        # chat_history.save_chat_message(user_id, session_id, 'assistant', response_content)
        
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

@app.post("/api/save_message")
async def save_message(
    message: SaveMessageRequest,
    token: str = Depends(oauth2_scheme)
):
    """Save a single chat message for a user's session."""
    try:
        # Verify the user
        current_user = auth_service.get_current_user(token)
        if current_user['user_id'] != message.user_id:
            raise HTTPException(status_code=403, detail="Unauthorized user")

        # Save the message using ChatHistoryMySQL
        chat_history.save_chat_message(
            user_id=message.user_id,
            session_id=message.session_id,
            role=message.role,
            content=message.content
        )
        
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving message: {str(e)}")

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
        

@app.post("/api/refresh_token")
async def refresh_token(request: Request):
    try:
        # Get the refresh token from the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        current_user = auth_service.get_current_user(token)
        
        # Create a new access token
        new_token = auth_service.create_access_token(
            data={"sub": current_user['username'], "user_id": current_user['user_id']},
            expires_delta=timedelta(minutes=30)
        )
        
        return {
            "access_token": new_token,
            "token_type": "bearer"
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")   

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

    mysql_listener = MySQLChangeListener()
    listener_thread = threading.Thread(target=mysql_listener.monitor_changes, daemon=True)
    listener_thread.start()
    uvicorn.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        reload=os.getenv('RELOAD', 'false').lower() == 'true'
    )


