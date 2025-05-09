from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain import hub
from langchain_google_genai import ChatGoogleGenerativeAI
from config import configg
import os


class QueryEngine:
    def __init__(self):
        """Initialize the QueryEngine with an optional index."""
        # Create the QA prompt for contextual queries
        self.prompt= self.create_prompt()
        self.config = configg
        self.llm = self.initialize_gemini_model()  # Initialize the Google Gemini model
        

    def initialize_gemini_model(self):
        """Initialize the Google Gemini model."""

        if not self.config:
            raise ValueError("Google Gemini API key or model name is not configured.")
        
        return ChatGoogleGenerativeAI(model=self.config.MODEL_NAME,google_api_key=self.config.MODEL_API_KEY)

    def create_prompt(self):
        """Create a prompt template for contextual queries."""
        prompt = hub.pull("rlm/rag-prompt")
        return prompt

    def query(self,retriever,query,use_context=False):
        """
        Query either the Gemini model or the query engine depending on context availability.
        
        :param query: The user's query.
        :param use_context: Whether to include contextual data from the index.
        """
        print(use_context)
        if use_context:
            rag_chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
            response=rag_chain.invoke(query)
            print(retriever.invoke(query))
        else:
            # Directly interact with the Gemini model
            print("Querying Gemini model directly without context.")
            prompt = f"Answer the following question using your prior knowledge:\nQuery: {query}\nAnswer:"
            response = self.llm.invoke(prompt)  # Use the Gemini model's completion method
        return response


