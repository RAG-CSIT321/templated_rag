import os
MODEL_NAME= 'gemini-1.5-flash'
MODEL_API_KEY= 'AIzaSyCCDH1LZgcluEGoXnJRyrEZ21aLTBXScK0'
MODEL_EMBEDDING_NAME= 'models/embedding-001'
class Config:
    def __init__(self):
        self.MODEL_NAME = MODEL_NAME
        self.MODEL_API_KEY = MODEL_API_KEY
        self.MODEL_EMBEDDING_NAME = MODEL_EMBEDDING_NAME
configg = Config()