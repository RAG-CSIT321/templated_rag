# Templated RAG System

A powerful Retrieval-Augmented Generation (RAG) system that combines document processing, database integration, and AI-powered chat capabilities. This system enhances language model responses by retrieving relevant context from your documents and databases.

🏆 **Award Winner**: 3rd Prize in Autumn Tech Expo 2025 at the University of Wollongong

## Features

- 🤖 AI-powered chat interface using Google's Gemini model
- 📚 Document processing for multiple file types (PDF, TXT, CSV, DOCX, Images)
- 🔄 Real-time MySQL database integration with change monitoring
- 🔍 Vector-based semantic search using Redis
- 👤 User authentication and session management
- 💬 Persistent chat history
- 🐳 Docker containerization for easy deployment

## System Architecture

The system consists of several key components:

1. **Query Engine**: Handles RAG implementation using Gemini model
2. **File Processor**: Processes and embeds documents
3. **Data Storage**: Manages vector storage in Redis
4. **MySQL Integration**: Handles database connections and change monitoring
5. **Authentication Service**: Manages user authentication and sessions

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- MySQL 8.0+
- Redis

## Setup

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd templated_rag
```

2. Configure environment variables:
Create a `.env` file with the following variables:
```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=chathistory
REDIS_URL=redis://redis:6379
SECRET_KEY=your_secret_key
```

3. Start the services:
```bash
docker-compose up -d
```

### Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up MySQL database:
- Create a database named `chathistory`
- Run the initialization scripts in `chat_history_mysql.py`

3. Configure environment variables (same as Docker setup)

4. Start Redis server

5. Run the application:
```bash
python main.py
```

## Usage

1. **Access the Web Interface**
   - Open `http://localhost:5000` in your browser
   - Log in with your credentials

2. **Upload Documents**
   - Navigate to the upload section
   - Upload PDF, TXT, CSV, DOCX, or image files
   - Files will be automatically processed and embedded

3. **Connect MySQL Database**
   - Go to the database connection section
   - Enter your MySQL credentials
   - The system will automatically monitor and process database changes

4. **Chat Interface**
   - Start a new chat session
   - Ask questions about your documents or database
   - The system will retrieve relevant context and generate responses

## API Endpoints

- `POST /api/interact_with_agent`: Send messages to the RAG system
- `POST /api/save_message`: Save chat messages
- `GET /api/chat_history`: Retrieve chat history
- `POST /api/upload`: Upload documents
- `POST /api/connect_database`: Connect MySQL database

## Testing

Run the test suite:
```bash
pytest
```

For coverage report:
```bash
pytest --cov=.
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

## Support

For issues and feature requests, please create an issue in the repository. 
