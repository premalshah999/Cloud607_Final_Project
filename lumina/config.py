"""
Application Configuration Module

This module defines configuration settings for the Lumina application.
Configuration values are loaded from environment variables with sensible defaults
for local development.

Environment Variables:
    SECRET_KEY      - Flask session encryption key (REQUIRED in production)
    DB_HOST         - MySQL host (default: localhost)
    DB_PORT         - MySQL port (default: 3306)
    DB_USER         - MySQL username (default: root)
    DB_PASSWORD     - MySQL password (default: empty)
    DB_NAME         - MySQL database name (default: lumina)
    
    Storage Backend (choose one):
    STORAGE_BACKEND - 'mongodb' or 'dynamodb' (default: mongodb)
    
    MongoDB Configuration:
    MONGO_URI       - MongoDB connection string (default: mongodb://localhost:27017)
    MONGO_DB        - MongoDB database name (default: lumina)
    
    AWS/DynamoDB Configuration:
    AWS_REGION          - AWS region (default: us-east-1)
    AWS_ACCESS_KEY_ID   - AWS access key
    AWS_SECRET_ACCESS_KEY - AWS secret key
    S3_BUCKET           - S3 bucket name for images
    DYNAMODB_PHOTOS_TABLE   - DynamoDB table for photos (default: lumina_photos)
    DYNAMODB_COMMENTS_TABLE - DynamoDB table for comments (default: lumina_comments)
    DYNAMODB_MESSAGES_TABLE - DynamoDB table for messages (default: lumina_messages)
"""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    """
    Application configuration class.
    
    Uses environment variables for production flexibility while providing
    sensible defaults for local development.
    
    Supports two storage backends:
        - MongoDB (default): For local development with Docker
        - DynamoDB + S3: For AWS deployment (Free Tier compatible)
    """
    
    # Directory configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STATIC_DIR: Path = BASE_DIR / 'static'

    # Security - MUST be set in production
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

    # Storage backend selection: 'mongodb' or 'dynamodb'
    STORAGE_BACKEND: str = os.environ.get('STORAGE_BACKEND', 'mongodb')

    # MySQL configuration (user authentication & friendships)
    DB_HOST: str = os.environ.get('DB_HOST', 'localhost')
    DB_PORT: int = int(os.environ.get('DB_PORT', '3306'))
    DB_USER: str = os.environ.get('DB_USER', 'root')
    DB_PASSWORD: str = os.environ.get('DB_PASSWORD', '')
    DB_NAME: str = os.environ.get('DB_NAME', 'lumina')

    # MongoDB configuration (for STORAGE_BACKEND='mongodb')
    MONGO_URI: str = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB: str = os.environ.get('MONGO_DB', 'lumina')

    # AWS configuration (for STORAGE_BACKEND='dynamodb')
    AWS_REGION: str = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID: str = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY: str = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    S3_BUCKET: str = os.environ.get('S3_BUCKET', 'lumina-photos')
    DYNAMODB_PHOTOS_TABLE: str = os.environ.get('DYNAMODB_PHOTOS_TABLE', 'lumina_photos')
    DYNAMODB_COMMENTS_TABLE: str = os.environ.get('DYNAMODB_COMMENTS_TABLE', 'lumina_comments')
    DYNAMODB_MESSAGES_TABLE: str = os.environ.get('DYNAMODB_MESSAGES_TABLE', 'lumina_messages')

    # Image processing constraints
    MAX_FULL_WIDTH: int = 1200   # Maximum width for full-resolution images
    MAX_THUMB_WIDTH: int = 400   # Maximum width for thumbnail images
    MAX_THUMB_WIDTH: int = 400   # Maximum width for thumbnail images
