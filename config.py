import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # File upload configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB default
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx'}

    # API Keys
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    OCR_SPACE_API_KEY = os.getenv('OCR_SPACE_API_KEY')

    # Processing configuration
    OCR_LANGUAGES = ['en']
    PROCESSING_TIMEOUT = 300  # 5 minutes

    # Output configuration
    DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    CSV_ENCODING = 'utf-8'

    @staticmethod
    def init_app(app):
        # Create necessary directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)