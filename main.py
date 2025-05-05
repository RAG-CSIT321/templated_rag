import os
import json
import time
import logging
import threading
import mysql.connector
import redis
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from file_processor import FileProcessor
from query_engine import QueryEngine
from chat_history import ChatHistory
from store_data import StoreData
from embedding_worker import EmbeddingWorker  # Import EmbeddingWorker

# Cấu hình MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'your_database',  # Thay thế bằng tên cơ sở dữ liệu của bạn
}

# Khởi tạo ứng dụng FastAPI
app = FastAPI()

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

# Initialize EmbeddingWorker
embedding_worker = EmbeddingWorker(store_data)  # Tạo worker xử lý embedding

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Hàm kiểm tra bảng có thay đổi không (kiểm tra theo thời gian cập nhật)
def check_for_updates(last_checked_timestamp):
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT id, content, updated_at FROM documents 
        WHERE updated_at > %s
    """
    cursor.execute(query, (last_checked_timestamp,))
    updates = cursor.fetchall()
    cursor.close()
    connection.close()
    return updates

# Worker để polling MySQL và kiểm tra thay đổi
def poll_for_changes():
    last_checked_timestamp = "1970-01-01 00:00:00"  # Thời gian kiểm tra ban đầu
    while True:
        updates = check_for_updates(last_checked_timestamp)
        if updates:
            # Xử lý các bản ghi được cập nhật
            logging.info(f"Found {len(updates)} updates: {updates}")
            # Cập nhật lại thời gian kiểm tra để tránh lấy lại dữ liệu cũ
            last_checked_timestamp = updates[-1]['updated_at']
            # Gọi thêm các xử lý khác nếu cần, như embedding hoặc lưu trữ dữ liệu
            # Ví dụ: gọi worker embedding
        time.sleep(10)  # Kiểm tra mỗi 10 giây

# 🔥 Background Task: Redis Listener 🔥
def redis_listener():
    """
    Background thread that listens for embedding update requests from MySQL changes.
    When an update is received, it re-processes the text and stores the new embedding in Redis.
    """
    print("[📡] Starting Redis listener...")
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    pubsub = redis_client.pubsub()
    pubsub.subscribe("embedding_updates")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
            print(f"[📥] Redis received embedding update: {data}")
            text = data["text"]
            key = data["key"]
            metadata = data.get("metadata", {})

            # Store new embedding in Redis
            store_data.store_single_embedding_to_redis(text, key, metadata)
            print("[✅] Embedding stored in Redis.")

        except Exception as e:
            print(f"[❌] Error processing Redis message: {e}")

@app.on_event("startup")
async def startup_event():
    """Start Redis listener and MySQL poller in background threads when FastAPI starts."""
    # Start Redis listener and MySQL poller in background threads
    threading.Thread(target=redis_listener, daemon=True).start()
    threading.Thread(target=poll_for_changes, daemon=True).start()
    threading.Thread(target=embedding_worker.listen_for_changes, daemon=True).start()  # Start EmbeddingWorker

# Các endpoint API khác (giống như trước)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("chat_ui.html", {"request": request})

@app.post("/api/interact_with_agent")
async def interact_with_agent(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    session_id = data.get("session_id", "default")

    if file_processor.retriever is None:
        return JSONResponse(
            content={"messages": [{"role": "assistant", "content": "Please upload a file before asking questions."}]},
            status_code=400
        )

    try:
        use_context = True  # Bây giờ chắc chắn có retriever
        response = query_engine.query(file_processor.retriever, prompt, use_context=use_context)

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
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=False)



