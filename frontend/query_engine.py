from llama_index.core import PromptTemplate
from llama_index.llms.gemini import Gemini
import os


class QueryEngine:
    def __init__(self, index=None):
        """Initialize the QueryEngine with an optional index."""
        self.index = index
        self.query_engine = None  # Start with no query engine
        self.qa_prompt = self.create_prompt()  # Create the QA prompt for contextual queries
        self.llm = self.initialize_gemini_model()  # Initialize the Google Gemini model
        if self.index:
            self.setup_query_engine()  # Set up the query engine if an index is provided

    def initialize_gemini_model(self):
        """Initialize the Google Gemini model."""
        api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyAldbAVtknZ7ueoidvZltGcoNlJu_NIRmA")
        model_name = os.environ.get("MODEL_NAME", "models/gemini-pro")

        if not api_key or not model_name:
            raise ValueError("Google Gemini API key or model name is not configured.")
        
        return Gemini(model_name=model_name, api_key=api_key)

    def create_prompt(self):
        """Create a prompt template for contextual queries."""
        QA_PROMPT_TMPL = (
            "Your task is to answer questions using your prior knowledge and the context information provided below.\n"
            "If no context is available, answer based solely on your prior knowledge.\n"
            "Context information (if any):\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Query: {query_str}\n"
            "Answer: "
        )
        return PromptTemplate(QA_PROMPT_TMPL)

    def setup_query_engine(self):
        """Set up the query engine using the current index."""
        if not self.index:
            raise ValueError("Index is not set. Unable to set up the query engine.")
        
        self.query_engine = self.index.as_query_engine(similarity_top_k=2)
        self.query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": self.qa_prompt}
        )

    def update_index(self, index):
        """Update the index and reinitialize the query engine."""
        self.index = index
        self.setup_query_engine()

    def query(self, query_str, use_context=True):
        """
        Query either the Gemini model or the query engine depending on context availability.
        
        :param query_str: The user's query.
        :param use_context: Whether to include contextual data from the index.
        """
        if use_context and self.query_engine:
            # Use the query engine to process the query with context
            response = self.query_engine.query(query_str)
        else:
            # Directly interact with the Gemini model
            print("Querying Gemini model directly without context.")
            prompt = f"Answer the following question using your prior knowledge:\nQuery: {query_str}\nAnswer:"
            response = self.llm.complete(prompt)  # Use the Gemini model's completion method

        # Extract text from the response object
        if hasattr(response, 'text'):
            return response.text
        elif isinstance(response, str):
            return response
        else:
            return response


