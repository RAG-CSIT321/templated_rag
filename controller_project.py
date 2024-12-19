
import os
import tempfile
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import CTransformers
from langchain import HuggingFacePipeline
from langchain_google_genai import ChatGoogleGenerativeAI

from llm1.llm1_skills import runllm1
#configuration
MODEL_NAME= 'gemini-1.5-flash'
MODEL_API_KEY= 'AIzaSyCCDH1LZgcluEGoXnJRyrEZ21aLTBXScK0'
MODEL_EMBEDDING_NAME= 'models/embedding-001'
REDIS_HOST='redis-10465.c291.ap-southeast-2-1.ec2.redns.redis-cloud.com'
REDIS_PORT=10465
REDIS_PASSWORD='kUbEslokXEAF2KHMBc5wGv0GqDgMaA44'
REDIS_URL="redis://default:kUbEslokXEAF2KHMBc5wGv0GqDgMaA44@redis-10465.c291.ap-southeast-2-1.ec2.redns.redis-cloud.com:10465"

class config:
    def __init__(self):
        self.MODEL_NAME = MODEL_NAME
        self.MODEL_API_KEY = MODEL_API_KEY
        self.MODEL_EMBEDDING_NAME = MODEL_EMBEDDING_NAME
        self.REDIS_HOST = REDIS_HOST
        self.REDIS_PORT = REDIS_PORT
        self.REDIS_PASSWORD = REDIS_PASSWORD
        self.REDIS_URL = REDIS_URL
        
config = config()
def handle_request(llm,query,file_name):
    if llm == 1:
        return runllm1(file_name,config,query)
    else:
        llm2.runllm2(file_name,query)
