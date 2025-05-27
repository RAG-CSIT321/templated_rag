import mysql.connector
from mysql.connector import Error
import time
import logging
from store_data import StoreData
from embedding_mysql import embedding_mysql
import redis
import hashlib
import os
import json
from file_processor import FileProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLChangeListener:
    def __init__(self, host=None, port=None, user=None, password=None, database=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.store_data = StoreData()

    def connect_to_mysql(self, connection_params=None):
        """Establish connection to MySQL server."""
        try:
            # Use connection_params if provided, else use instance attributes
            params = connection_params or {
                'host': self.host,
                'port': self.port,
                'user': self.user,
                'password': self.password,
                'database': self.database
            }
            # Only proceed if all required params are present
            if not all(params.get(key) for key in ['host', 'port', 'user', 'password', 'database']):
                logger.error("Missing required connection parameters")
                return None
            connection = mysql.connector.connect(**params)
            return connection
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            return None


    def add_connection(self, connection_params):
        """
        Add a new database connection to monitor.
        
        Args:
            connection_params (dict): Connection parameters (host, port, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate a unique key for the connection (e.g., host:port)
            
            # Test the connection first
            conn = self.connect_to_mysql(connection_params)
            if conn:
                conn.close()
                # Add to connections dictionary
                
                # Save to Redis
                return True
            else:
                logger.error(f"Could not establish connection for MYSQL Listener")
                return False
        except Exception as e:
            logger.error(f"Error adding connection: {e}")
            return False

    def clear_redis_embeddings(self):
        """Clear all embeddings from Redis."""
        try:
            # Delete the index
            self.redis_client.flushdb()
            logging.info("Successfully cleared Redis embeddings")

        except Exception as e:
            logging.error(f"Error clearing Redis embeddings: {e}")
    def re_embed_all_files(self):
        """Re-embed all files in the data directory."""
        try:
            data_dir = "data"
            if not os.path.exists(data_dir):
                return

            for filename in os.listdir(data_dir):
                file_path = os.path.join(data_dir, filename)
                if os.path.isfile(file_path):
                    # Process each file
                    file_processor = FileProcessor()
                    file_processor.process_file(file_path)
                    logging.info(f"Re-embedded file: {filename}")
        except Exception as e:
            logging.error(f"Error re-embedding files: {e}")
    def update_embeddings(self):
        """Update embeddings with latest MySQL data."""
        try:
            # Get fresh data from MySQL
            documents = embedding_mysql(self.host,self.port,self.user,self.password,self.database)
            # Process and store new embeddings
            self.store_data.process_data(documents, False)
            logging.info("Successfully updated MySQL embeddings")
        
        # Re-embed all files in the data directory
            self.re_embed_all_files()
            logging.info("Successfully re-embedded all files")
            
            print("Successfully updated all embeddings")
        except Exception as e:
            logging.error(f"Error updating embeddings: {e}")
            
    def get_table_hash(self, cursor):
        """Get a hash of the current table content."""
        cursor.execute("SELECT * FROM test ")
        rows = cursor.fetchall()
        # Create a string representation of all rows
        content_str = str(rows)
        # Generate hash
        return hashlib.md5(content_str.encode()).hexdigest()
            
    def monitor_changes(self):
        """Monitor MySQL changes and update embeddings accordingly."""
        while True:
            try:
                connection = self.connect_to_mysql()
                if connection:
                    cursor = connection.cursor()
                    
                    # Get current table hash
                    current_hash = self.get_table_hash(cursor)
                    
                    # Store the hash for comparison
                    if not hasattr(self, 'last_hash'):
                        self.last_hash = current_hash
                    
                    # Check if there are any changes
                    if current_hash != self.last_hash:
                        print("Detected changes in MySQL")
                        logging.info("Detected changes in MySQL database")
                        # Clear existing embeddings
                        self.clear_redis_embeddings()
                        # Update with new data
                        self.update_embeddings()
                        # Update the hash
                        self.last_hash = current_hash
                    
                    cursor.close()
                    connection.close()
                
                # Wait for 5 seconds before checking again
                time.sleep(5)
                
            except Error as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    listener = MySQLChangeListener()
    listener.monitor_changes()