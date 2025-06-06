import mysql.connector
from langchain.schema import Document
import logging

logger = logging.getLogger(__name__)

def embedding_mysql(host, port, user, password, database):
    """
    Extract data from all tables in a MySQL database and convert it to Document objects for embedding.
    
    Args:
        host (str): Database host
        port (int): Database port
        user (str): Database username
        password (str): Database password
        database (str): Database name
        
    Returns:
        list: List of Document objects containing the data from all tables
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
        
        # Get all tables in the database
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        documents = []
        
        # Iterate through each table
        for table in tables:
            try:
                # Query each table
                cursor.execute(f"SELECT * FROM {table}")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                for row in rows:
                    contents = dict(zip(columns, row))
                    # Add table name as the source in metadata
                    content = "\n".join(f"{col}: {val}" for col, val in contents.items())
                    content = "{" + content + "}"
                    metadata = {'source': f'{database}.{table}'}
                    doc = Document(page_content=content, metadata=metadata)
                    documents.append(doc)
                
                logger.info(f"Successfully extracted data from table '{table}'")
                
            except mysql.connector.Error as err:
                logger.error(f"Error processing table '{table}': {err}")
                continue
        
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

