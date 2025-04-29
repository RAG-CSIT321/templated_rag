import os
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

class Config:
    GOOGLE_API_KEY = ""
    GEMINI_MODEL = "models/gemini-1.5-pro"
    EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

    @staticmethod
    def setup_environment():
        """Set environment variables for Google Gemini and model configuration."""
        os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY
        os.environ["MODEL_NAME"] = Config.GEMINI_MODEL

        # Initialize and configure the models
        llm = Gemini(
            model_name=os.environ["MODEL_NAME"],  # Use the model name from the environment variable
            api_key=os.environ["GOOGLE_API_KEY"]  # Use the API key from the environment variable
        )

        embed_model = HuggingFaceEmbedding(model_name=Config.EMBEDDING_MODEL)  # Use the embedding model

        # Set global settings in llama_index
        Settings.llm = llm
        Settings.embed_model = embed_model

        #print("Google Gemini LLM and HuggingFace embedding model configured successfully.")

