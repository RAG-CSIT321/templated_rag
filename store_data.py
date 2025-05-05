from langchain_community.vectorstores.redis import Redis as Rediss
from langchain_community.embeddings import HuggingFaceEmbeddings
from redis import Redis
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import configg
from embedding_mysql import embedding_mysql
import os
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

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
        self.url = "redis://localhost:6379"
        # Connect to Redis
        self.redis_client = Redis.from_url(self.url)
        self.embeddings = configg.MODEL_EMBEDDING_NAME
        self.index_name = "document_embeddings"  # Consistent index name
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

        # Check if index exists
        if self.redis_client.exists(self.index_name):
            # Add to existing index
            vstore = Rediss.from_existing_index(
                embedding=self.embeddings,
                redis_url=self.url,
                index_name=self.index_name
            )
            vstore.add_texts(
                texts=[text.page_content for text in texts],
                metadatas=[text.metadata for text in texts]
            )
        else:
            # Create new index
            vstore = Rediss.from_texts(
                texts=[text.page_content for text in texts],
                metadatas=[text.metadata for text in texts],
                embedding=self.embeddings,
                redis_url=self.url,
                index_name=self.index_name
            )
        
        print("success")
        self.retriever = vstore.as_retriever()
    def load_retriever(self):
        return self.retriever
    def store_mysql(self):
        self.process_data(embedding_mysql(),False)
