from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import json
import logging
import threading
import redis
from datetime import datetime
import time

from file_processor import FileProcessor
from query_engine import QueryEngine
from chat_history_mysql import ChatHistoryMySQL
from store_data import StoreData
from mysql_listener import MySQLChangeListener

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth_service import AuthService, SECRET_KEY, ALGORITHM
from pydantic import BaseModel
from typing import Optional

# Get port from environment variable (for Render.com)
PORT = int(os.getenv("PORT", 5000))

# Define a model for the request body
class SaveMessageRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    role: str
    content: str
app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your actual domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates setup
templates = Jinja2Templates(directory="templates")


# Initialize components
chat_history = ChatHistoryMySQL()
query_engine = QueryEngine()
file_processor = FileProcessor(data_dir="data")
store_data = StoreData()
mysql_listener = MySQLChangeListener()

# Skip default database initialization - we'll only use client-provided databases
logger.info("Initialized RAG system - waiting for client database connections or file uploads")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth_service = AuthService()

@app.post("/api/register")
async def register_user(
    request: Request  # Add this to accept raw JSON
):
    data = await request.json()  # Get JSON data
    try:
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'user')  # Default to 'user' if not specified
        
        # Check if username exists before attempting registration
        if auth_service.check_username_exists(username):
            return JSONResponse(content={
                "status": "error",
                "detail": "Username already taken. Please choose another username."
            }, status_code=400)
            
        result = auth_service.register_user(
            username,
            password,
            email,
            role
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

@app.get("/client", response_class=HTMLResponse)
async def client_dashboard(request: Request):
    return templates.TemplateResponse("client_dashboard.html", {"request": request})

@app.post("/api/connect_database")
async def connect_database(request: Request, token: str = Depends(oauth2_scheme)):
    try:
        current_user = auth_service.get_current_user(token)
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if current_user['role'] != "client":
            raise HTTPException(status_code=403, detail="Only clients can connect databases")
            
        data = await request.json()
        
        # Get the host from the request
        host = data.get('host')
        # If connecting to localhost/127.0.0.1, use the Docker service name
        if host in ['localhost', '127.0.0.1']:
            host = 'mysql'
            
        connection_params = {
            'host': host,
            'port': data.get('port'),
            'user': data.get('username'),  # Map 'username' to 'user' for MySQL
            'password': data.get('password'),
            'database': data.get('database')
        }
        
        if not all([connection_params[key] for key in ['host', 'port', 'user', 'password', 'database']]):
            raise HTTPException(status_code=400, detail="All database connection fields are required")
            
        # Test the connection first
        try:
            store_data.store_mysql(
                host=connection_params['host'],
                port=connection_params['port'],
                user=connection_params['user'],
                password=connection_params['password'],
                database=connection_params['database']
            )
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to connect to database: {str(e)}")
            
        file_processor.retriever = store_data.load_retriever()
        
        # Initialize MySQL listener with connection parameters
        global mysql_listener
        mysql_listener = MySQLChangeListener(
            host=connection_params['host'],
            port=connection_params['port'],
            user=connection_params['user'],
            password=connection_params['password'],
            database=connection_params['database']
        )
        
        if mysql_listener.add_connection(connection_params):
            listener_thread = threading.Thread(target=mysql_listener.monitor_changes, daemon=True)
            listener_thread.start()
            return JSONResponse(content={
                "status": "success",
                "message": "Database connected successfully. Your data is being processed and will be used for AI responses."
            })
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to database")
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interact_with_agent")
async def interact_with_agent(request: Request, token: str = Depends(oauth2_scheme)):
    current_user = auth_service.get_current_user(token)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    logger.info(f"Received request body: {data}")

    user_id = current_user['user_id']
    session_id = data.get('session_id')

    if not session_id:
        session_id = chat_history.create_new_session(
            user_id=user_id,
            session_name=f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
        )
        logger.info(f"Created new session: {session_id}")

    if not user_id or not session_id:
        logger.error(f"Missing user_id or session_id: user_id={user_id}, session_id={session_id}")
        raise HTTPException(status_code=400, detail="User ID and Session ID are required")
    
    try:
        prompt = data.get('prompt', '')
        logger.info(f"Processing query: {prompt}")

        # Load chat history from MySQL
        history = chat_history.load_chat_history(user_id, session_id)
        chat_messages = history.get('messages', []) if history else []
        
        # Process the query with chat history
        use_context = file_processor.retriever is not None
        response = query_engine.query(
            file_processor.retriever, 
            prompt, 
            use_context=use_context,
            chat_history=chat_messages  # Pass the loaded messages to query engine
        )
        # Get response content
        response_content = response.content if hasattr(response, "content") else str(response)
        if not response_content.strip():
            response_content = "I don't have enough information to answer that question. Please upload relevant files to provide more context."
        
        return JSONResponse(content={
            "messages": [{"role": "assistant", "content": response_content}],
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        # Return a graceful error message instead of server error
        return JSONResponse(
            content={
                "messages": [{
                    "role": "assistant", 
                    "content": "I'm sorry, I encountered an issue processing your question. Please try again or upload some relevant documents to help me answer better."
                }],
                "session_id": session_id
            },
            status_code=200
        )
        
@app.options("/api/interact_with_agent")
async def handle_options():
    return JSONResponse(content={})

@app.post("/api/save_message")
async def save_message(
    message: SaveMessageRequest,
    token: str = Depends(oauth2_scheme)
):
    """Save a single chat message for a user's session. Creates session if needed."""
    try:
        # Verify the user
        current_user = auth_service.get_current_user(token)
        if current_user['user_id'] != message.user_id:
            raise HTTPException(status_code=403, detail="Unauthorized user")

        # If no session_id provided, create a new session
        if not message.session_id:
            session_id = chat_history.create_new_session(
                user_id=message.user_id,
                session_name=f"Chat {datetime.now().strftime('%m/%d %H:%M')}"
            )
        else:
            session_id = message.session_id

        # Save the message
        chat_history.save_chat_message(
            user_id=message.user_id,
            session_id=session_id,
            role=message.role,
            content=message.content
        )
        
        return JSONResponse(content={"status": "success", "session_id": session_id})
    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving message: {str(e)}")

@app.post("/api/upload_file")
async def upload_file(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    try:
        # Get user from token
        current_user = auth_service.get_current_user(token)
        user_id = current_user['user_id']
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No selected file")

        file_path = os.path.join("data", file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        logger.info(f"Processing file {file.filename} for client")
        result = file_processor.process_file(file_path, user_id)
        
        # Trigger upload history refresh for the client
        return JSONResponse(content={
            "message": result,
            "status": "success",
            "file_path": file_path,
            "file_name": file.filename
        })
    except Exception as e:
        logger.error(f"Upload file error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

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
            data={"sub": current_user['username'], "user_id": current_user['user_id'], "role": current_user['role']},
            expires_delta=timedelta(minutes=30)
        )
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "role": current_user['role']
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

@app.get("/api/list_files")
async def list_files(token: str = Depends(oauth2_scheme)):
    try:
        # Get user from token
        current_user = auth_service.get_current_user(token)
        user_id = current_user['user_id']
        
        # Get list of files from the data directory
        files = []
        data_dir = "data"
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                file_path = os.path.join(data_dir, filename)
                if os.path.isfile(file_path):
                    files.append({
                        "filename": filename,
                        "size": os.path.getsize(file_path),
                        "uploaded_at": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
        
        return JSONResponse(content={
            "status": "success",
            "files": files
        })
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/delete_file/{filename}")
async def delete_file(filename: str, token: str = Depends(oauth2_scheme)):
    try:
        # Get user from token
        current_user = auth_service.get_current_user(token)
        user_id = current_user['user_id']
        
        file_path = os.path.join("data", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
            
        # Delete the file
        os.remove(file_path)
        
        # Update embeddings in MySQL listener
        if mysql_listener:
            # First clear all embeddings
            mysql_listener.clear_redis_embeddings()
            # Then update embeddings with remaining files
            mysql_listener.update_embeddings()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"File {filename} deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    

    uvicorn.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=PORT,
        reload=os.getenv('RELOAD', 'false').lower() == 'true'
    )


