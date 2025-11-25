"""
Lumina Package - Flask Application Factory

This module implements the Flask application factory pattern, which provides:
    - Clean separation of configuration and application code
    - Easy testing with different configurations
    - Multiple application instances if needed

The factory pattern is a Flask best practice for production applications.

Storage Backends:
    - MongoDB (default): Uses MongoDB + GridFS for photo storage
    - DynamoDB: Uses AWS DynamoDB + S3 for fully managed AWS storage
    
Set STORAGE_BACKEND environment variable to 'mongodb' or 'dynamodb'.
"""

from __future__ import annotations

from flask import Flask, send_from_directory

from .config import Config
from .routes import api_blueprint, auth_blueprint


def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Application factory function.
    
    Creates and configures a Flask application instance with:
        - MySQL connection for user authentication
        - Storage backend (MongoDB or DynamoDB) for photo storage
        - REST API blueprints for photos and authentication
        - Session-based authentication
    
    Args:
        config_class: Configuration class to use (default: Config)
                      Can be overridden for testing purposes.
    
    Returns:
        Flask: Configured Flask application instance
    
    Example:
        >>> app = create_app()
        >>> app.run(debug=True)
    """
    config = config_class()
    
    # Initialize Flask with static file configuration
    app = Flask(__name__, static_folder=str(config.STATIC_DIR), static_url_path='/static')
    app.config.from_object(config)
    app.secret_key = config.SECRET_KEY
    
    # Image processing configuration
    app.config['MAX_FULL_WIDTH'] = config.MAX_FULL_WIDTH
    app.config['MAX_THUMB_WIDTH'] = config.MAX_THUMB_WIDTH

    # Initialize storage layer based on STORAGE_BACKEND setting
    if config.STORAGE_BACKEND == 'dynamodb':
        from .storage_dynamodb import StorageDynamoDB
        storage = StorageDynamoDB(config)
        app.logger.info("Using DynamoDB + S3 storage backend")
    else:
        from .storage import Storage
        storage = Storage(config)
        app.logger.info("Using MongoDB storage backend")
    
    app.extensions['photo_storage'] = storage

    # Register API blueprints with /api prefix
    app.register_blueprint(api_blueprint, url_prefix='/api')
    app.register_blueprint(auth_blueprint, url_prefix='/api')

    @app.route('/')
    def index():
        """Serve the single-page application HTML."""
        return send_from_directory(str(config.BASE_DIR), 'app.html')

    return app
