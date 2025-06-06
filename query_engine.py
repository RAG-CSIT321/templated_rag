from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain import hub
from langchain_google_genai import ChatGoogleGenerativeAI
from config import configg
from langchain.prompts import PromptTemplate
import os
from typing import List, Dict, Optional
from langchain.schema import Document

class QueryEngine:
    def __init__(self):
        """Initialize the QueryEngine with an optional index."""
        # Create the QA prompt for contextual queries
        self.prompt = self.create_prompt()
        self.config = configg
        self.llm = self.initialize_gemini_model()  # Initialize the Google Gemini model

    def initialize_gemini_model(self):
        """Initialize the Google Gemini model."""

        if not self.config:
            raise ValueError("Google Gemini API key or model name is not configured.")
        
        return ChatGoogleGenerativeAI(model=self.config.MODEL_NAME,google_api_key=self.config.MODEL_API_KEY)

    def summarize_chat_history(self, messages: List[Dict]) -> str:
        """
        Summarize the chat history using the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            str: A concise summary of the chat history
        """
        if not messages:
            return ""
            
        # Format messages for summarization
        chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        # Create summarization prompt
        summary_prompt = f"""
        Please provide in detail summary of the following chat history. Focus on the main topics:
        
        {chat_text}
        
        Summary:
        """
        # Get summary from LLM and extract content
        summary = self.llm.invoke(summary_prompt)
        result = summary.content if hasattr(summary, 'content') else str(summary)
        print(f"Summary: {result}")
        return result

    def create_prompt(self):
        """Create a prompt template for contextual queries."""
        #You have access to the following context about tech items such as computers, monitors, keyboards, etc.
        prompt = """
        You are a helpful and friendly assistant that answers questions clearly and concisely.
        Instructions:
        1. If the question is simple or general,use your general knowledge to provide a clear and informative answer, regardless of the context.
        2. If the question is specific and the context contains relevant information, use that context to provide a detailed answer.
        3. Do not explicitly state whether you're using context or general knowledge - just provide a natural, helpful response.

        Context:
        {context}

        Previous conversation summary:
        {chat_summary}

        Question:
        {question}

        Answer:
        """
        return PromptTemplate.from_template(prompt)

    def enhance_query(self, query: str, chat_history: List[Dict]) -> str:
        """
        Enhance the query by incorporating context from chat history.
        """
        if not chat_history:
            return query

        # Get the last few messages for context
        last_messages = chat_history[-5:]  # Get last 3 messages
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in last_messages])
        
        # Create a simpler prompt to enhance the query
        enhancement_prompt = f"""
        Based on the chat history and current question, create a clear and focused search query.
        Keep the query structured and relevant to the original question.
        Do not add speculative options or make assumptions.
        if the question is already clear and concise,just return the question.

        Chat history:
        {context}

        Current question: {query}

        Enhanced query:"""
        
        enhanced_query = self.llm.invoke(enhancement_prompt)
        result = enhanced_query.content if hasattr(enhanced_query, 'content') else str(enhanced_query)
        # Clean up the response to remove any extra formatting or explanations
        result = result.strip().split('\n')[0]  # Take only the first line
        print(f"Enhanced query: {result}")
        return result

    def format_docs(self, docs: List[Document]) -> str:
        """
        Combines all page_content from a list of Document objects into one string.

        Args:
            docs (List[Document]): List of LangChain Document objects.

        Returns:
            str: Combined string of all document contents.
        """
        return "\n\n".join(doc.page_content for doc in docs if doc.page_content)

    def query(self, retriever, query: str, use_context: bool = False, chat_history: Optional[List[Dict]] = None):
        """
        Query either the Gemini model or the query engine depending on context availability.
        """
        # Summarize chat history if available
        chat_summary = self.summarize_chat_history(chat_history) if chat_history else ""
        if use_context:
            enhanced_query = self.enhance_query(query, chat_history) if chat_history else query
            print(f"Using enhanced query for retrieval: {enhanced_query}")
            print(retriever.invoke(enhanced_query))
            rag_chain = (
                {
                    "context": retriever | self.format_docs,
                    "question": RunnablePassthrough(),
                    "chat_summary": lambda _: chat_summary
                }
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
            response = rag_chain.invoke(enhanced_query)
        else:
            # Directly interact with the Gemini model
            print("Querying Gemini model directly without context.")
            prompt = f"""
            Previous conversation summary:
            {chat_summary}
            
            Answer the following question using your prior knowledge:
            Query: {query}
            Answer:"""
            response = self.llm.invoke(prompt)
            
        return response