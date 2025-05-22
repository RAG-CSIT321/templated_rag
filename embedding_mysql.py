import mysql.connector
from langchain.schema import Document
import logging

logger = logging.getLogger(__name__)

def embedding_mysql(host, port, user, password, database):
    """
    Extract data from a MySQL database table and convert it to Document objects for embedding.
    
    Args:
        host (str): Database host
        port (int): Database port
        user (str): Database username
        password (str): Database password
        database (str): Database name
        table (str, optional): Specific table to extract data from. If None, extracts from all tables.
        
    Returns:
        list: List of Document objects containing the data
    """
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        # Query
        cursor.execute("SELECT * FROM test")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
            
        documents = []
        
        for row in rows:
            contents = dict(zip(columns, row))
            # Add movies_database as the id
            content = "\n".join(f"{col}: {val}" for col, val in contents.items())
            content = "{" + content + "}"
            metadata = {'source': 'movies_database'}
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
        
        # Cleanup
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully extracted {len(documents)} documents from database '{database}'")
        return documents
    
    except mysql.connector.Error as err:
        logger.error(f"Database error: {err}")
        return []
    except Exception as e:
        logger.error(f"Error processing database: {e}")
        return []

