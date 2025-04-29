from langchain_community.vectorstores.redis import Redis as RedisVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from redis import Redis
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import configg
import os
class StoreData:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.config = configg
        self.retriever = None
        self.url ="redis://localhost:6379"
        # Connect to Redis
        self.redis_client = Redis.from_url(self.url)
        self.embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
    def process_data(self,documents,split):
        """Process files and store the index in Redis."""
        if self.redis_client.ping():
            print("✅ Redis server is up and running!")
        else:
            print("❌ Failed to connect to Redis.")
        texts=None
        # Split text into chunks
        if split:
            splitter = RecursiveCharacterTextSplitter(chunk_size=256, chunk_overlap=50)
            texts = splitter.split_documents(documents)
        else:
            texts = documents
        url = "redis://localhost:6379"
        vstore = Redis.from_texts(
            texts= [text.page_content for text in texts],
            metadata = [text.metadata for text in texts],
            embedding=self.embeddings,
            redis_url=url,
        )
        self.retriever = vstore.as_retriever()
    def load_retriever(self):
        return self.retriever