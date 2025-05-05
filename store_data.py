from langchain_community.vectorstores.redis import Redis as RedisVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from redis import Redis
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import configg
import os
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

class StoreData:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.config = configg
        self.retriever = None
        self.url = "redis://localhost:6379"
        
        # Configure logging
        self.logger = logging.getLogger('StoreData')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize connections
        self.redis_client = self._init_redis()
        self.embeddings = HuggingFaceEmbeddings(model_name=self.config.MODEL_EMBEDDING_NAME)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _init_redis(self):
        """Initialize Redis connection with retry logic"""
        return Redis.from_url(self.url)

    def check_redis_connection(self):
        """Check if Redis is available"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            self.logger.error(f"Redis connection error: {str(e)}")
            return False

    def process_data(self, documents, split=True):
        """Process documents and store in Redis"""
        if not self.check_redis_connection():
            raise ConnectionError("Cannot connect to Redis server")

        try:
            if split:
                splitter = RecursiveCharacterTextSplitter(chunk_size=256, chunk_overlap=50)
                texts = splitter.split_documents(documents)
            else:
                texts = documents

            vstore = RedisVectorStore.from_texts(
                texts=[text.page_content for text in texts],
                metadata=[text.metadata for text in texts],
                embedding=self.embeddings,
                redis_url=self.url,
                index_name="documents"
            )
            self.retriever = vstore.as_retriever()
            self.logger.info(f"Processed {len(texts)} documents into Redis")
        except Exception as e:
            self.logger.error(f"Error processing documents: {str(e)}")
            raise

    def load_retriever(self):
        """Load the retriever instance"""
        if not self.retriever:
            self.logger.warning("Retriever not initialized, creating new one")
            self.retriever = RedisVectorStore(
                redis_url=self.url,
                index_name="documents",
                embedding=self.embeddings
            ).as_retriever()
        return self.retriever

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def store_single_embedding_to_redis(self, text, redis_key, metadata=None):
        """Store single embedding with retry logic"""
        try:
            embedding = self.embeddings.embed_query(text)
            data = {
                "embedding": embedding,
                "metadata": metadata or {},
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
            self.redis_client.set(redis_key, json.dumps(data))
            self.logger.info(f"Stored embedding for key: {redis_key}")
        except Exception as e:
            self.logger.error(f"Error storing embedding: {str(e)}")
            raise

    def listen_for_embedding_updates(self, channel='embedding_updates'):
        """Listen for embedding updates via Redis pub/sub"""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)
        self.logger.info(f"Listening for messages on channel: {channel}")

        for message in pubsub.listen():
            if message['type'] != 'message':
                continue
            try:
                data = json.loads(message['data'])
                self.logger.info(f"Received embedding update: {data}")
                
                text = data['text']
                key = data['key']
                metadata = data.get('metadata', {})
                
                self.store_single_embedding_to_redis(text, key, metadata)
            except Exception as e:
                self.logger.error(f"Error processing Redis message: {str(e)}")