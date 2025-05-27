import os
import threading
import logging
from store_data import StoreData
from langchain_core.documents import Document
from langchain_community.document_loaders import CSVLoader,PyPDFLoader,WebBaseLoader,TextLoader,Docx2txtLoader
from langchain_community.document_loaders.image import UnstructuredImageLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileProcessor:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.ensure_data_directory()
        self.retriever = None
    def ensure_data_directory(self):
        """Ensure that the data directory exists."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def validate_file(self, file_path):
        """Validates the uploaded file."""
        file_type = file_path.split('.')[-1].lower()
        if file_type not in ['jpg', 'jpeg', 'png', 'csv', 'pdf', 'txt']:
            return False, f"Unsupported file type: {file_type}"
        return True, None

    def process_file(self, file_path, on_file_uploaded=None):
        """
        Processes the uploaded file, extracts content, and updates the index.

        Args:
            file_path (str): The path to the uploaded file.
            on_file_uploaded (function): Optional callback for further actions.

        Returns:
            str: Success or error message.
        """
        try:
            # Validate file type
            is_valid, error_message = self.validate_file(file_path)
            if not is_valid:
                return error_message

            # Get file extension and base name
            file_type = file_path.split('.')[-1].lower()
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            documentss = None
            split = True

            # Process based on file type
            if file_type in ['jpg', 'jpeg', 'png']:  # Image files
                logger.info(f"Starting OCR processing for image: {file_path}")
                try:
                    loader = UnstructuredImageLoader(file_path)
                    documentss = loader.load()
                    if documentss and len(documentss) > 0:
                        logger.info(f"OCR Success! Extracted {len(documentss)} text segments")
                        logger.info(f"First segment content: {documentss[0].page_content[:200]}...")
                    else:
                        logger.warning("OCR completed but no text was extracted")
                    print("File process succeed")
                except Exception as ocr_error:
                    logger.error(f"OCR processing failed: {str(ocr_error)}")
                    return f"OCR processing failed: {str(ocr_error)}"
            # Process the CSV file
            elif file_type == 'csv':  # CSV files
                loader = CSVLoader(file_path=file_path)
                documentss = loader.load()
                split =False
                print("File process succeed")
            elif file_type == "docx":
                loader = Docx2txtLoader(file_path=file_path)
                documentss = loader.load()
            elif file_type == 'pdf':  # PDF files
                loader = PyPDFLoader(file_path=file_path)
                documentss = loader.load()
                print("File process succeed")
            elif file_type == 'txt':  # Text files
                loader = TextLoader(file_path, encoding='utf-8')
                documentss = loader.load()
                print("File process succeed")

            # Trigger StoreData processing and update the index
            store = StoreData()
            # Load the index from Redis
            store.process_data(documentss,split)
            self.retriever = store.load_retriever()


        except Exception as e:
            return f"Error processing file: {str(e)}"

    def process_file_api(self, params):
        """
        API for processing files via Pywebview.

        Args:
            params (dict): A dictionary containing 'file_path'.

        Returns:
            dict: Status and message for the operation.
        """
        file_path = params.get("file_path")
        if not file_path:
            return {"status": "error", "message": "No file path provided"}

        result = self.process_file(file_path)
        return {"status": "success", "message": result}

    def process_file_async(self, file_path, on_file_uploaded=None):
        """
        Processes the file asynchronously to avoid blocking the main thread.

        Args:
            file_path (str): The path to the uploaded file.
            on_file_uploaded (function): Optional callback for further actions.
        """
        threading.Thread(target=self.process_file, args=(file_path, on_file_uploaded)).start()