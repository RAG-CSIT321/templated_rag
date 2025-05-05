import redis
import json
import logging
import time
from store_data import StoreData

class EmbeddingWorker:
    def __init__(self, store_data: StoreData):
        self.store_data = store_data
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0)
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe("embedding_updates")
    
    def process_embedding(self, text: str, key: str, metadata: dict = None):
        """
        Process the embedding and store it.
        """
        try:
            # Process embedding for the text (placeholder for actual embedding logic)
            embedding = self.store_data.generate_embedding(text)
            
            # Store embedding in Redis
            self.store_data.store_single_embedding_to_redis(text, key, metadata)
            logging.info(f"[✅] Embedding for key: {key} stored successfully.")
        except Exception as e:
            logging.error(f"[❌] Error processing embedding for key {key}: {e}")
    
    def listen_for_changes(self):
        """
        Listen for embedding update requests from Redis and process the updates.
        """
        logging.info("[📡] Embedding Worker started listening for changes.")
        
        for message in self.pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                logging.info(f"[📥] Embedding update received: {data}")
                
                text = data["text"]
                key = data["key"]
                metadata = data.get("metadata", {})
                
                # Process the received embedding update
                self.process_embedding(text, key, metadata)
            except Exception as e:
                logging.error(f"[❌] Error processing Redis message: {e}")
    
    def poll_for_updates(self, last_checked_timestamp: str):
        """
        Poll for updates from the MySQL database and process the changes.
        """
        try:
            updates = self.check_for_mysql_updates(last_checked_timestamp)
            if updates:
                logging.info(f"Found {len(updates)} updates to process.")
                last_checked_timestamp = updates[-1]['updated_at']
                
                # Process the updates (embedding or storage as necessary)
                for update in updates:
                    text = update["content"]
                    key = update["id"]
                    metadata = update.get("metadata", {})
                    self.process_embedding(text, key, metadata)
            return last_checked_timestamp
        except Exception as e:
            logging.error(f"[❌] Error polling for MySQL updates: {e}")
            return last_checked_timestamp
    
    def check_for_mysql_updates(self, last_checked_timestamp: str):
        """
        Check for changes in MySQL database (documents table).
        """
        try:
            # Query MySQL to get documents updated after the last check
            connection = self.store_data.get_mysql_connection()
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT id, content, updated_at FROM documents
                WHERE updated_at > %s
            """
            cursor.execute(query, (last_checked_timestamp,))
            updates = cursor.fetchall()
            cursor.close()
            connection.close()
            return updates
        except Exception as e:
            logging.error(f"[❌] Error checking MySQL for updates: {e}")
            return []
    
    def run_polling(self):
        """
        Run a polling loop to periodically check for MySQL updates.
        """
        last_checked_timestamp = "1970-01-01 00:00:00"  # Initial timestamp
        while True:
            last_checked_timestamp = self.poll_for_updates(last_checked_timestamp)
            time.sleep(10)  # Poll every 10 seconds
