import os
from dotenv import load_dotenv

# Load .env.local first (takes precedence), then .env as fallback
load_dotenv('.env.local')
load_dotenv('.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    
    # Use local PostgreSQL connection for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://fatinmojumder@localhost:5432/nda_redline'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.environ.get('JWT_SECRET') or 'dev-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    CORS_ORIGINS = [os.environ.get('CORS_ORIGIN', 'http://localhost:3000')]
    
    # Mock OpenAI key for development
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or 'mock-key-for-development'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
