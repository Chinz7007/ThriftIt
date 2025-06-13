import os
from datetime import timedelta

class Config:
    """Application configuration class"""
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///products.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload Security
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Socket.IO Configuration
    SOCKETIO_ASYNC_MODE = 'threading'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries

class ProductionConfig(Config):
    """Production configuration"""  
    DEBUG = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}