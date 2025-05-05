import time
import mysql.connector
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent
)
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import json
from datetime import datetime
from store_data import StoreData

class MySQLWatcher:
    def __init__(self, db_config):
        """
        Improved MySQL watcher using binlog replication instead of polling
        
        Args:
            db_config (dict): MySQL connection configuration
        """
        self.db_config = db_config
        self.store_data = StoreData()
        self.logger = logging.getLogger('MySQLWatcher')
        self.last_processed_time = datetime.now()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def connect_to_mysql(self):
        """Establish MySQL connection with retry logic"""
        return mysql.connector.connect(**self.db_config)

    def normalize_metadata(self, row_data, action_type):
        """
        Standardize metadata format between MySQL and Redis
        
        Args:
            row_data (dict): Row data from MySQL
            action_type (str): Type of operation (insert/update/delete)
            
        Returns:
            dict: Normalized metadata
        """
        return {
            'source': 'mysql',
            'action': action_type,
            'mysql_id': row_data.get('id'),
            'timestamp': datetime.now().isoformat(),
            'original_data': row_data
        }

    def extract_text(self, row_data):
        """
        Extract text content from MySQL row data
        
        Args:
            row_data (dict): Row data from MySQL
            
        Returns:
            str: Extracted text content
        """
        # Customize this based on your table structure
        if 'content' in row_data:
            return row_data['content']
        elif 'text' in row_data:
            return row_data['text']
        else:
            return str(row_data)

    def process_change(self, event, row):
        """
        Process different types of database changes
        
        Args:
            event: Binlog event
            row: Changed row data
        """
        try:
            if isinstance(event, WriteRowsEvent):
                self.handle_insert(row['values'])
            elif isinstance(event, UpdateRowsEvent):
                self.handle_update(row['before_values'], row['after_values'])
            elif isinstance(event, DeleteRowsEvent):
                self.handle_delete(row['values'])
        except Exception as e:
            self.logger.error(f"Error processing change: {str(e)}")

    def handle_insert(self, row_data):
        """Handle new row insertions"""
        text = self.extract_text(row_data)
        metadata = self.normalize_metadata(row_data, 'insert')
        
        self.store_data.store_single_embedding_to_redis(
            text=text,
            redis_key=f"mysql:{row_data['id']}",
            metadata=metadata
        )
        self.logger.info(f"Processed INSERT for record {row_data['id']}")

    def handle_update(self, before_data, after_data):
        """Handle row updates"""
        text = self.extract_text(after_data)
        metadata = self.normalize_metadata(after_data, 'update')
        
        self.store_data.store_single_embedding_to_redis(
            text=text,
            redis_key=f"mysql:{after_data['id']}",
            metadata=metadata
        )
        self.logger.info(f"Processed UPDATE for record {after_data['id']}")

    def handle_delete(self, row_data):
        """Handle row deletions"""
        redis_key = f"mysql:{row_data['id']}"
        self.store_data.redis_client.delete(redis_key)
        self.logger.info(f"Processed DELETE for record {row_data['id']}")

    def start_listening(self):
        """Start listening for MySQL changes using binlog"""
        self.logger.info("Starting MySQL binlog listener...")
        
        stream = BinLogStreamReader(
            connection_settings=self.db_config,
            server_id=100,  # Unique server ID
            blocking=True,
            only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
            resume_stream=True,
            only_schemas=[self.db_config['database']]  # Only watch specified database
        )

        try:
            for binlogevent in stream:
                self.last_processed_time = datetime.now()
                for row in binlogevent.rows:
                    self.process_change(binlogevent, row)
        except Exception as e:
            self.logger.error(f"Error in binlog stream: {str(e)}")
            raise
        finally:
            stream.close()
            self.logger.info("MySQL binlog listener stopped")

    def run(self):
        """Main entry point to start the watcher"""
        while True:
            try:
                self.start_listening()
            except Exception as e:
                self.logger.error(f"Watcher crashed, restarting: {str(e)}")
                time.sleep(5)  # Wait before restarting