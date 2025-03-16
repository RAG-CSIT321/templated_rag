import os
import shutil
import pandas as pd
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
import io
from store_data import StoreData
import threading

class FileProcessor:
    def __init__(self, data_dir="data", query_engine=None):
        self.data_dir = data_dir
        self.query_engine = query_engine  # Inject the QueryEngine instance
        self.ensure_data_directory()

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

            # Copy the file to the 'data' directory
            file_path_in_data = os.path.join(self.data_dir, f"{base_name}_original.{file_type}")
            shutil.copy(file_path, file_path_in_data)

            text_content = ""

            # Process based on file type
            if file_type in ['jpg', 'jpeg', 'png']:  # Image files
                image = Image.open(file_path)
                text_content = pytesseract.image_to_string(image)

            elif file_type == 'csv':  # CSV files
                df = pd.read_csv(file_path)
                text_content = df.head().to_string()

            elif file_type == 'pdf':  # PDF files
                with open(file_path, "rb") as f:
                    pdf_bytes = f.read()
                pdf_file = io.BytesIO(pdf_bytes)

                reader = PdfReader(pdf_file)
                text = ""

                for page in reader.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        text += extracted_text

                if text.strip():
                    text_content = text.strip()
                else:
                    pdf_file.seek(0)
                    images = convert_from_bytes(pdf_file.read())
                    ocr_text = ""
                    for i, image in enumerate(images):
                        ocr_text += f"\nPage {i + 1}:\n"
                        ocr_text += pytesseract.image_to_string(image)
                    text_content = ocr_text.strip()

            elif file_type == 'txt':  # Text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read().strip()

            # Save extracted text to a file in the 'data' directory
            text_file_path = os.path.join(self.data_dir, f"{base_name}_processed.txt")
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)

            # Trigger StoreData processing and update the index
            storage = StoreData(data_dir=self.data_dir)
            index = storage.process_data()

            if self.query_engine:
                self.query_engine.update_index(index)

            # Notify the system via callback, if provided
            if on_file_uploaded:
                on_file_uploaded(file_path_in_data)

            return f"File saved to {file_path_in_data}. Data processed and index updated successfully!"

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
