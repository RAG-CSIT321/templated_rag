import os
from langchain_huggingface import HuggingFaceEmbeddings
MODEL_NAME= 'gemini-1.5-flash'
MODEL_API_KEY= 'AIzaSyCCDH1LZgcluEGoXnJRyrEZ21aLTBXScK0'

class Config:
    def __init__(self):
        self.MODEL_NAME = MODEL_NAME
        self.MODEL_API_KEY = MODEL_API_KEY
        self.MODEL_EMBEDDING_NAME = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
configg = Config()
